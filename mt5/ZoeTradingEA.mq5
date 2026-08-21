//+------------------------------------------------------------------+
//| ZoeTradingEA.mq5                                                 |
//| Companion panel for zoeTrading V1. Logic stays in Python.         |
//+------------------------------------------------------------------+
#property strict
#property version   "0.5"
#property description "zoeTrading companion panel: status, mode, approval and kill switch."

input string Zoe_StatusFile = "zoetrading_status.csv";
input string Zoe_CommandFile = "zoetrading_command.csv";
input int    Zoe_PanelCorner = CORNER_LEFT_UPPER;

string PREFIX = "ZOE_";
string mode = "MANUAL";
string system_status = "PAUSED";
string last_signal = "NO SIGNAL";
string last_strategy = "-";
string last_regime = "-";
string last_score = "-";
string last_entry = "-";
string last_sl = "-";
string last_tp = "-";
string last_risk = "-";
string last_decision_id = "-";
string previous_decision_id = "-";
datetime g_last_read_ok = 0;
int      g_last_open_error = 0;

int OnInit()
{
   DrawPanel();
   EventSetTimer(1);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, PREFIX);
}

void OnTimer()
{
   LoadStatus();
   DrawPanel();
   UpdateChartAnnotations();
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id != CHARTEVENT_OBJECT_CLICK)
      return;

   if(sparam == PREFIX + "APPROVE") WriteCommand("APPROVE");
   if(sparam == PREFIX + "REJECT") WriteCommand("REJECT");
   if(sparam == PREFIX + "PAUSE") WriteCommand("PAUSE");
   if(sparam == PREFIX + "KILL") WriteCommand("KILL_SWITCH");
   if(sparam == PREFIX + "RESUME") WriteCommand("RESUME");

   // OBJ_BUTTON stays visually pressed after a click until OBJPROP_STATE is
   // reset -- without this, buttons can look stuck down and stop reliably
   // firing CHARTEVENT_OBJECT_CLICK on a second click.
   if(ObjectFind(0, sparam) >= 0)
      ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
}

// FileOpen used to fail silently here -- the panel just stayed stuck on its
// compile-time defaults ("Status: PAUSED | Signal: NO SIGNAL") forever, with
// nothing anywhere (not even the Experts log) saying why. That made a path
// or permission problem on the operator's machine indistinguishable from
// "nothing to show yet", and impossible to diagnose remotely. Now every
// open failure is logged once (with the real Windows/MT5 error code) and
// every successful read is timestamped so the panel itself can show when
// the last update actually happened.
void LoadStatus()
{
   int handle = FileOpen(Zoe_StatusFile, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      int err = GetLastError();
      if(err != g_last_open_error)
      {
         PrintFormat(
            "zoeTrading: FileOpen a echoue pour '%s' (FILE_COMMON), erreur=%d. "
            "Verifie que Python ecrit bien dans %%APPDATA%%\\MetaQuotes\\Terminal\\Common\\Files\\, "
            "que le terminal n'est pas en mode portable, et que Zoe_StatusFile est reste "
            "a sa valeur par defaut dans les Inputs de l'EA.",
            Zoe_StatusFile, err
         );
         g_last_open_error = err;
      }
      return;
   }
   g_last_open_error = 0;

   while(!FileIsEnding(handle))
   {
      string key = FileReadString(handle);
      string value = FileReadString(handle);
      if(key == "status") system_status = value;
      if(key == "mode") mode = value;
      if(key == "signal") last_signal = value;
      if(key == "strategy") last_strategy = value;
      if(key == "regime") last_regime = value;
      if(key == "score") last_score = value;
      if(key == "entry") last_entry = value;
      if(key == "sl") last_sl = value;
      if(key == "tp") last_tp = value;
      if(key == "risk") last_risk = value;
      if(key == "decision_id") last_decision_id = value;
   }
   FileClose(handle);
   g_last_read_ok = TimeCurrent();
}

// Writes the button click together with the decision_id currently shown,
// so the Python side only ever executes a click that matches the exact
// proposal the human was looking at (never a stale one from a prior scan).
void WriteCommand(string command)
{
   int handle = FileOpen(Zoe_CommandFile, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON);
   if(handle == INVALID_HANDLE)
      return;
   FileWrite(handle, "command", command);
   FileWrite(handle, "decision_id", last_decision_id);
   FileWrite(handle, "time", TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS));
   FileClose(handle);
}

// The status file always carries the single best decision across every
// scanned instrument, not just this chart's symbol -- an operator glancing
// at Entry/SL/TP on the wrong chart is a real, easy mistake. These two
// helpers are the single source of truth for whether the currently shown
// signal actually belongs to this chart, used by both the panel (to warn)
// and the chart annotations (to decide whether to draw at all).
bool HasTradeSignal()
{
   return (StringFind(last_signal, "NO SIGNAL") < 0) && (StringFind(last_signal, "NO_TRADE") < 0);
}

// last_signal is always "<BUY|SELL> <instrument>" (write_status_file's
// format); the instrument is everything after the first space, which can
// itself contain spaces (e.g. "Volatility 75 Index"). Comparing this for
// exact equality -- instead of a substring search across the whole
// "<action> <instrument>" text -- avoids any risk of one symbol name
// matching as a false positive because it happens to appear inside another.
string SignalInstrument()
{
   int space_pos = StringFind(last_signal, " ");
   if(space_pos < 0)
      return "";
   return StringSubstr(last_signal, space_pos + 1);
}

bool SignalMatchesChart()
{
   return HasTradeSignal() && (SignalInstrument() == _Symbol);
}

void DrawPanel()
{
   int x = 12;
   int y = 18;
   bool other_chart = HasTradeSignal() && !SignalMatchesChart();
   string signal_text = "Signal: " + last_signal + " | Strategy: " + last_strategy;
   if(other_chart)
      signal_text += "  <<< AUTRE GRAPHIQUE (" + _Symbol + ")";
   color signal_color = other_chart ? clrOrange : clrLightGray;

   // Surface a broken/stale link between Python and this chart directly on
   // the panel -- previously a failed or stopped connection looked exactly
   // like "nothing to show yet" (Status stuck on the compile-time default
   // "PAUSED"), which is impossible to tell apart from normal idle MONITORING
   // at a glance. See the Experts log for the exact FileOpen error code.
   string status_text;
   color status_color;
   if(g_last_read_ok == 0)
   {
      status_text = "Status: AUCUNE DONNEE RECUE" + (g_last_open_error != 0 ? " (erreur " + IntegerToString(g_last_open_error) + ", voir Experts)" : " (en attente...)");
      status_color = clrOrangeRed;
   }
   else
   {
      int stale_seconds = (int)(TimeCurrent() - g_last_read_ok);
      if(stale_seconds > 10)
      {
         status_text = "Status: " + system_status + " | Mode: " + mode + "  (perime depuis " + IntegerToString(stale_seconds) + "s)";
         status_color = clrOrangeRed;
      }
      else
      {
         status_text = "Status: " + system_status + " | Mode: " + mode;
         status_color = clrLightGray;
      }
   }

   DrawLabel("TITLE", "zoeTrading", x, y, 13, clrWhite);
   DrawLabel("STATUS", status_text, x, y + 22, 9, status_color);
   DrawLabel("SIGNAL", signal_text, x, y + 42, 9, signal_color);
   DrawLabel("REGIME", "Regime: " + last_regime + " | Score: " + last_score, x, y + 62, 9, clrLightGray);
   DrawLabel("LEVELS", "Entry: " + last_entry + " | SL: " + last_sl + " | TP: " + last_tp, x, y + 82, 9, clrLightGray);
   DrawLabel("RISK", "Risk: " + last_risk, x, y + 102, 9, clrLightGray);

   DrawButton("APPROVE", "APPROVE", x, y + 130, 80, 24, clrSeaGreen);
   DrawButton("REJECT", "REJECT", x + 88, y + 130, 80, 24, clrDimGray);
   DrawButton("PAUSE", "PAUSE", x + 176, y + 130, 70, 24, clrDarkOrange);
   DrawButton("KILL", "KILL", x + 254, y + 130, 70, 24, clrFireBrick);
   DrawButton("RESUME", "RESUME", x, y + 158, 80, 24, clrDodgerBlue);
}

// Draws Entry/SL/TP price lines and a BUY/SELL arrow on the chart, but only
// when the displayed signal is for the instrument this chart is showing --
// the same status file can carry a signal for a different symbol, and
// drawing price lines from another instrument here would be misleading.
void UpdateChartAnnotations()
{
   bool for_this_symbol = SignalMatchesChart();

   double entry = for_this_symbol ? StringToDoubleSafe(last_entry) : 0.0;
   double sl = for_this_symbol ? StringToDoubleSafe(last_sl) : 0.0;
   double tp = for_this_symbol ? StringToDoubleSafe(last_tp) : 0.0;

   DrawOrRemoveLevel(PREFIX + "ENTRY", entry, clrWhite, "zoe entry");
   DrawOrRemoveLevel(PREFIX + "SL", sl, clrFireBrick, "zoe SL");
   DrawOrRemoveLevel(PREFIX + "TP", tp, clrSeaGreen, "zoe TP");

   if(for_this_symbol && last_decision_id != previous_decision_id && last_decision_id != "-")
   {
      if(StringFind(last_signal, "BUY") == 0)
         DrawSignalArrow(OBJ_ARROW_BUY, entry, clrSeaGreen);
      else if(StringFind(last_signal, "SELL") == 0)
         DrawSignalArrow(OBJ_ARROW_SELL, entry, clrFireBrick);
   }
   previous_decision_id = last_decision_id;
}

double StringToDoubleSafe(string value)
{
   if(value == "-" || value == "")
      return 0.0;
   return StringToDouble(value);
}

void DrawOrRemoveLevel(string name, double price, color line_color, string label_text)
{
   if(price <= 0.0)
   {
      if(ObjectFind(0, name) >= 0)
         ObjectDelete(0, name);
      return;
   }
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, line_color);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetString(0, name, OBJPROP_TEXT, label_text);
}

void DrawSignalArrow(ENUM_OBJECT arrow_type, double price, color arrow_color)
{
   double anchor_price = price > 0.0 ? price : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   // Each new decision_id got its own permanent arrow object, name and all,
   // and nothing ever removed the previous one -- over a long-running
   // session the chart accumulates one arrow per proposal forever. Only the
   // current signal's arrow is meaningful, so clear old ones first.
   ObjectsDeleteAll(0, PREFIX + "ARROW_");
   string name = PREFIX + "ARROW_" + last_decision_id;
   ObjectCreate(0, name, arrow_type, 0, TimeCurrent(), anchor_price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, arrow_color);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
}

void DrawLabel(string name, string text, int x, int y, int size, color text_color)
{
   string object_name = PREFIX + name;
   if(ObjectFind(0, object_name) < 0)
      ObjectCreate(0, object_name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, object_name, OBJPROP_CORNER, Zoe_PanelCorner);
   ObjectSetInteger(0, object_name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, object_name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, object_name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, object_name, OBJPROP_COLOR, text_color);
   ObjectSetString(0, object_name, OBJPROP_TEXT, text);
}

void DrawButton(string name, string text, int x, int y, int w, int h, color bg)
{
   string object_name = PREFIX + name;
   if(ObjectFind(0, object_name) < 0)
      ObjectCreate(0, object_name, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, object_name, OBJPROP_CORNER, Zoe_PanelCorner);
   ObjectSetInteger(0, object_name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, object_name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, object_name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, object_name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, object_name, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, object_name, OBJPROP_COLOR, clrWhite);
   ObjectSetString(0, object_name, OBJPROP_TEXT, text);
}
