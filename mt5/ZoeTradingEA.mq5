//+------------------------------------------------------------------+
//| ZoeTradingEA.mq5                                                 |
//| Companion panel for zoeTrading V1. Logic stays in Python.         |
//+------------------------------------------------------------------+
#property strict
#property version   "0.1"
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
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id != CHARTEVENT_OBJECT_CLICK)
      return;

   if(sparam == PREFIX + "APPROVE") WriteCommand("APPROVE");
   if(sparam == PREFIX + "REJECT") WriteCommand("REJECT");
   if(sparam == PREFIX + "PAUSE") WriteCommand("PAUSE");
   if(sparam == PREFIX + "KILL") WriteCommand("KILL_SWITCH");
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
   }
   FileClose(handle);
}

void WriteCommand(string command)
{
   int handle = FileOpen(Zoe_CommandFile, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON);
   if(handle == INVALID_HANDLE)
      return;
   FileWrite(handle, "command", command);
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

