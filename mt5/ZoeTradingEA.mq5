//+------------------------------------------------------------------+
//| ZoeTradingEA.mq5                                                 |
//| Companion panel for zoeTrading V1. Logic stays in Python.         |
//+------------------------------------------------------------------+
#property strict
#property version   "0.3"
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
}

void LoadStatus()
{
   int handle = FileOpen(Zoe_StatusFile, FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON);
   if(handle == INVALID_HANDLE)
      return;

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

void DrawPanel()
{
   int x = 12;
   int y = 18;
   DrawLabel("TITLE", "zoeTrading", x, y, 13, clrWhite);
   DrawLabel("STATUS", "Status: " + system_status + " | Mode: " + mode, x, y + 22, 9, clrLightGray);
   DrawLabel("SIGNAL", "Signal: " + last_signal + " | Strategy: " + last_strategy, x, y + 42, 9, clrLightGray);
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
   bool for_this_symbol = (StringFind(last_signal, _Symbol) >= 0)
                        && (StringFind(last_signal, "NO SIGNAL") < 0)
                        && (StringFind(last_signal, "NO_TRADE") < 0);

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

void DrawSignalArrow(int arrow_type, double price, color arrow_color)
{
   double anchor_price = price > 0.0 ? price : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   string name = PREFIX + "ARROW_" + last_decision_id;
   if(ObjectFind(0, name) < 0)
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
