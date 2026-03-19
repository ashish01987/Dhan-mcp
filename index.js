import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";

const CLIENT_ID    = process.env.DHAN_CLIENT_ID    || "YOUR_CLIENT_ID";
const ACCESS_TOKEN = process.env.DHAN_ACCESS_TOKEN || "YOUR_ACCESS_TOKEN";
const BASE        = "https://api.dhan.co/v2";
const H = { "Content-Type": "application/json", "access-token": ACCESS_TOKEN };

async function GET(p)      { const r = await fetch(BASE+p,{headers:H}); const d=await r.json(); if(!r.ok) throw new Error(JSON.stringify(d)); return d; }
async function POST(p,b)   { const r = await fetch(BASE+p,{method:"POST",  headers:H,body:JSON.stringify(b)}); const d=await r.json(); if(!r.ok) throw new Error(JSON.stringify(d)); return d; }
async function PUT(p,b)    { const r = await fetch(BASE+p,{method:"PUT",   headers:H,body:JSON.stringify(b)}); const d=await r.json(); if(!r.ok) throw new Error(JSON.stringify(d)); return d; }
async function DEL(p)      { const r = await fetch(BASE+p,{method:"DELETE",headers:H}); if(r.status===202||r.status===200){try{return await r.json();}catch{return{status:"OK"};}} throw new Error(await r.text()); }
async function DEL_B(p,b)  { const r = await fetch(BASE+p,{method:"DELETE",headers:H,body:JSON.stringify(b)}); if(r.status===202||r.status===200){try{return await r.json();}catch{return{status:"OK"};}} throw new Error(await r.text()); }

const server = new Server({ name:"dhan-mcp-server", version:"3.0.0" },{ capabilities:{tools:{}} });

// ═══════════════════════════════════════════════════════════════════════════
// TOOL DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [

  // ── CORE ─────────────────────────────────────────────────────────────────
  { name:"get_fund_limits",  description:"Get available fund limits / margin",        inputSchema:{type:"object",properties:{},required:[]} },
  { name:"get_holdings",     description:"Get all equity holdings in demat",          inputSchema:{type:"object",properties:{},required:[]} },
  { name:"get_positions",    description:"Get current open intraday/short positions", inputSchema:{type:"object",properties:{},required:[]} },
  { name:"get_order_list",   description:"Get all orders placed today",               inputSchema:{type:"object",properties:{},required:[]} },
  { name:"get_order_by_id",  description:"Get details of a specific order",
    inputSchema:{type:"object",properties:{order_id:{type:"string"}},required:["order_id"]} },
  { name:"cancel_order",     description:"Cancel a pending regular order",
    inputSchema:{type:"object",properties:{order_id:{type:"string"}},required:["order_id"]} },
  { name:"get_quote",        description:"Get live LTP. securities = {NSE_EQ:['1333']}",
    inputSchema:{type:"object",properties:{securities:{type:"object"}},required:["securities"]} },
  { name:"get_market_depth", description:"Get full order book for instruments",
    inputSchema:{type:"object",properties:{securities:{type:"object"}},required:["securities"]} },
  { name:"get_ohlc",         description:"Get OHLC snapshot for instruments",
    inputSchema:{type:"object",properties:{securities:{type:"object"}},required:["securities"]} },
  { name:"get_trade_history",description:"Get trade history between two dates",
    inputSchema:{type:"object",properties:{from_date:{type:"string"},to_date:{type:"string"},page:{type:"number"}},required:["from_date","to_date"]} },
  { name:"place_order",      description:"Place a regular buy/sell order",
    inputSchema:{type:"object",required:["security_id","exchange_segment","transaction_type","order_type","product_type","quantity","price","validity"],
    properties:{security_id:{type:"string"},exchange_segment:{type:"string"},transaction_type:{type:"string"},
      order_type:{type:"string"},product_type:{type:"string"},quantity:{type:"number"},price:{type:"number"},
      trigger_price:{type:"number"},validity:{type:"string"},tag:{type:"string"}}} },

  // ── CANDLE DATA ───────────────────────────────────────────────────────────
  { name:"get_intraday_candles", description:"Intraday OHLCV candles. interval: 1/5/15/25/60",
    inputSchema:{type:"object",required:["security_id","exchange_segment","instrument_type","interval","from_date","to_date"],
    properties:{security_id:{type:"string"},exchange_segment:{type:"string"},instrument_type:{type:"string"},
      interval:{type:"string"},from_date:{type:"string"},to_date:{type:"string"}}} },
  { name:"get_daily_candles",    description:"Daily/weekly/monthly candles. interval: D/W/M",
    inputSchema:{type:"object",required:["security_id","exchange_segment","instrument_type","from_date","to_date"],
    properties:{security_id:{type:"string"},exchange_segment:{type:"string"},instrument_type:{type:"string"},
      from_date:{type:"string"},to_date:{type:"string"}}} },

  // ── FOREVER ORDERS (GTT + OCO) ────────────────────────────────────────────
  { name:"create_forever_order", description:"Create a Forever/GTT order. orderFlag: SINGLE or OCO (one-cancels-other). OCO needs price1/triggerPrice1/quantity1 for the second leg.",
    inputSchema:{type:"object",required:["security_id","exchange_segment","transaction_type","product_type","order_type","validity","quantity","price","trigger_price","order_flag"],
    properties:{security_id:{type:"string"},exchange_segment:{type:"string"},transaction_type:{type:"string"},
      product_type:{type:"string"},order_type:{type:"string"},validity:{type:"string"},
      order_flag:{type:"string",description:"SINGLE or OCO"},
      quantity:{type:"number"},price:{type:"number"},trigger_price:{type:"number"},
      price1:{type:"number",description:"OCO target price"},
      trigger_price1:{type:"number",description:"OCO target trigger"},
      quantity1:{type:"number",description:"OCO target qty"}}} },
  { name:"modify_forever_order", description:"Modify a forever order's price, qty, trigger, or validity",
    inputSchema:{type:"object",required:["order_id","order_flag","order_type","leg_name","quantity","price","trigger_price","validity"],
    properties:{order_id:{type:"string"},order_flag:{type:"string"},order_type:{type:"string"},
      leg_name:{type:"string",description:"TARGET_LEG or STOP_LOSS_LEG"},
      quantity:{type:"number"},price:{type:"number"},trigger_price:{type:"number"},validity:{type:"string"}}} },
  { name:"cancel_forever_order", description:"Cancel a forever order by order ID",
    inputSchema:{type:"object",properties:{order_id:{type:"string"}},required:["order_id"]} },
  { name:"get_forever_orders",   description:"List all active forever/GTT orders",
    inputSchema:{type:"object",properties:{},required:[]} },

  // ── SUPER ORDERS (entry + target + SL + trailing in one call) ─────────────
  { name:"place_super_order", description:"Place a Super Order with entry, target price, stop-loss and optional trailing stop — all in one call. Needs static IP whitelisted on Dhan.",
    inputSchema:{type:"object",required:["security_id","exchange_segment","transaction_type","product_type","order_type","quantity","price","target_price","stop_loss_price","trailing_jump"],
    properties:{security_id:{type:"string"},exchange_segment:{type:"string"},
      transaction_type:{type:"string",description:"BUY or SELL"},
      product_type:{type:"string",description:"CNC / INTRADAY / MARGIN / MTF"},
      order_type:{type:"string",description:"LIMIT or MARKET"},
      quantity:{type:"number"},price:{type:"number"},
      target_price:{type:"number",description:"Target exit price"},
      stop_loss_price:{type:"number",description:"Stop loss trigger price"},
      trailing_jump:{type:"number",description:"Price jump by which SL trails (0 = no trailing)"},
      correlation_id:{type:"string"}}} },
  { name:"modify_super_order", description:"Modify a super order leg. leg_name: ENTRY_LEG / TARGET_LEG / STOP_LOSS_LEG",
    inputSchema:{type:"object",required:["order_id","leg_name"],
    properties:{order_id:{type:"string"},
      leg_name:{type:"string",description:"ENTRY_LEG / TARGET_LEG / STOP_LOSS_LEG"},
      order_type:{type:"string"},quantity:{type:"number"},price:{type:"number"},
      target_price:{type:"number"},stop_loss_price:{type:"number"},trailing_jump:{type:"number"}}} },
  { name:"cancel_super_order", description:"Cancel a super order leg or the entire super order. leg: ENTRY_LEG / TARGET_LEG / STOP_LOSS_LEG",
    inputSchema:{type:"object",required:["order_id","order_leg"],
    properties:{order_id:{type:"string"},order_leg:{type:"string",description:"ENTRY_LEG / TARGET_LEG / STOP_LOSS_LEG"}}} },
  { name:"get_super_orders",   description:"List all super orders for today",
    inputSchema:{type:"object",properties:{},required:[]} },

  // ── CONDITIONAL TRIGGERS (algo-style: price/indicator → auto place order) ─
  { name:"create_conditional_trigger", description:"Place an order automatically when a price or technical indicator condition is met. Supports SMA, EMA, RSI etc. with operators like CROSSING_UP, ABOVE, BELOW.",
    inputSchema:{type:"object",required:["security_id","exchange_segment","comparison_type","operator","exp_date","frequency","orders"],
    properties:{
      security_id:{type:"string"},
      exchange_segment:{type:"string",description:"NSE_EQ / BSE_EQ / IDX_I"},
      comparison_type:{type:"string",description:"PRICE_TO_VALUE / TECHNICAL_WITH_VALUE / TECHNICAL_WITH_TECHNICAL"},
      indicator_name:{type:"string",description:"SMA_5 / SMA_10 / EMA_9 / RSI_14 etc. (omit for price comparison)"},
      time_frame:{type:"string",description:"DAY / ONE_MIN / FIVE_MIN / FIFTEEN_MIN"},
      operator:{type:"string",description:"CROSSING_UP / CROSSING_DOWN / ABOVE / BELOW / EQUAL"},
      comparing_value:{type:"number",description:"Price or indicator value to compare against"},
      comparing_indicator:{type:"string",description:"Second indicator name for TECHNICAL_WITH_TECHNICAL"},
      exp_date:{type:"string",description:"Alert expiry date YYYY-MM-DD"},
      frequency:{type:"string",description:"ONCE or RECURRING"},
      user_note:{type:"string"},
      orders:{type:"array",description:"Array of order objects to place when triggered",
        items:{type:"object",properties:{
          transaction_type:{type:"string"},exchange_segment:{type:"string"},product_type:{type:"string"},
          order_type:{type:"string"},security_id:{type:"string"},quantity:{type:"number"},
          validity:{type:"string"},price:{type:"number"},trigger_price:{type:"number"}}}}}} },
  { name:"get_all_triggers",   description:"List all active conditional triggers",
    inputSchema:{type:"object",properties:{},required:[]} },
  { name:"delete_trigger",     description:"Delete a conditional trigger by alert ID",
    inputSchema:{type:"object",properties:{alert_id:{type:"string"}},required:["alert_id"]} },

  // ── TRADER'S CONTROL (risk management) ────────────────────────────────────
  { name:"set_kill_switch",    description:"ACTIVATE or DEACTIVATE trading for the day. All positions must be closed before activating.",
    inputSchema:{type:"object",properties:{status:{type:"string",description:"ACTIVATE or DEACTIVATE"}},required:["status"]} },
  { name:"get_kill_switch",    description:"Check if kill switch is currently active or not",
    inputSchema:{type:"object",properties:{},required:[]} },
  { name:"set_pnl_exit",       description:"Configure auto-exit when profit or loss threshold is reached. All positions are squared off automatically.",
    inputSchema:{type:"object",required:["profit_value","loss_value","product_type"],
    properties:{profit_value:{type:"number",description:"Auto-exit when profit reaches this value"},
      loss_value:{type:"number",description:"Auto-exit when loss reaches this value"},
      product_type:{type:"array",items:{type:"string"},description:"Array: INTRADAY and/or DELIVERY"},
      enable_kill_switch:{type:"boolean",description:"Also activate kill switch when triggered"}}} },
  { name:"get_pnl_exit",       description:"View current P&L based exit configuration",
    inputSchema:{type:"object",properties:{},required:[]} },
  { name:"stop_pnl_exit",      description:"Disable the active P&L based exit rule",
    inputSchema:{type:"object",properties:{},required:[]} },

  // ── MARGIN CALCULATOR ─────────────────────────────────────────────────────
  { name:"calculate_margin",   description:"Calculate margin, brokerage and leverage required before placing an order",
    inputSchema:{type:"object",required:["security_id","exchange_segment","transaction_type","quantity","product_type","price"],
    properties:{security_id:{type:"string"},exchange_segment:{type:"string"},
      transaction_type:{type:"string"},quantity:{type:"number"},
      product_type:{type:"string"},price:{type:"number"},trigger_price:{type:"number"}}} },
  { name:"calculate_margin_multi", description:"Calculate margin for a basket of multiple orders at once",
    inputSchema:{type:"object",required:["orders"],
    properties:{include_positions:{type:"boolean"},include_orders:{type:"boolean"},
      orders:{type:"array",items:{type:"object",properties:{
        security_id:{type:"string"},exchange_segment:{type:"string"},
        transaction_type:{type:"string"},quantity:{type:"number"},
        product_type:{type:"string"},price:{type:"number"}}}}}} },

  // ── LEDGER ────────────────────────────────────────────────────────────────
  { name:"get_ledger",         description:"Get account ledger with all debit/credit transactions and running balance",
    inputSchema:{type:"object",properties:{from_date:{type:"string"},to_date:{type:"string"}},required:["from_date","to_date"]} },

  // ── P&L ANALYSIS (computed) ───────────────────────────────────────────────
  { name:"get_pnl_summary",    description:"Compute P&L summary from holdings and positions",
    inputSchema:{type:"object",properties:{},required:[]} },
  { name:"get_trade_pnl",      description:"Compute realized P&L from trade history between two dates",
    inputSchema:{type:"object",properties:{from_date:{type:"string"},to_date:{type:"string"}},required:["from_date","to_date"]} },

  // ── OPTION CHAIN ─────────────────────────────────────────────────────────
  { name:"get_option_chain",   description:"Full option chain with CE/PE OI, IV, Greeks. NIFTY=13, BANKNIFTY=25",
    inputSchema:{type:"object",required:["underlying_security_id","exchange_segment","expiry_date"],
    properties:{underlying_security_id:{type:"string"},exchange_segment:{type:"string"},expiry_date:{type:"string"}}} },
  { name:"get_expiry_dates",   description:"Available expiry dates for an underlying",
    inputSchema:{type:"object",required:["underlying_security_id","exchange_segment","instrument_type"],
    properties:{underlying_security_id:{type:"string"},exchange_segment:{type:"string"},instrument_type:{type:"string"}}} },

]}));

// ═══════════════════════════════════════════════════════════════════════════
// TOOL HANDLERS
// ═══════════════════════════════════════════════════════════════════════════
server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: a } = req.params;
  try {
    let r;
    switch(name) {

    // ── CORE ────────────────────────────────────────────────────────────────
    case "get_fund_limits":   r = await GET("/fundlimit"); break;
    case "get_holdings":      r = await GET("/holdings");  break;
    case "get_positions":     r = await GET("/positions"); break;
    case "get_order_list":    r = await GET("/orders");    break;
    case "get_order_by_id":   r = await GET(`/orders/${a.order_id}`); break;
    case "cancel_order":      r = await DEL(`/orders/${a.order_id}`); break;
    case "get_quote":         r = await POST("/marketfeed/ltp",  a.securities); break;
    case "get_market_depth":  r = await POST("/marketfeed/full", a.securities); break;
    case "get_ohlc":          r = await POST("/marketfeed/ohlc", a.securities); break;
    case "get_trade_history": r = await GET(`/trades/${a.from_date}/${a.to_date}/${a.page??0}`); break;
    case "place_order":
      r = await POST("/orders",{
        dhanClientId:CLIENT_ID, securityId:a.security_id, exchangeSegment:a.exchange_segment,
        transactionType:a.transaction_type, orderType:a.order_type, productType:a.product_type,
        quantity:a.quantity, price:a.price, triggerPrice:a.trigger_price??0,
        validity:a.validity, tag:a.tag??"", afterMarketOrder:false });
      break;

    // ── CANDLES ─────────────────────────────────────────────────────────────
    case "get_intraday_candles":
      r = await POST("/charts/intraday",{
        securityId:a.security_id, exchangeSegment:a.exchange_segment,
        instrument:a.instrument_type, interval:a.interval,
        fromDate:a.from_date, toDate:a.to_date }); break;
    case "get_daily_candles":
      r = await POST("/charts/historical",{
        securityId:a.security_id, exchangeSegment:a.exchange_segment,
        instrument:a.instrument_type, expiryCode:0,
        fromDate:a.from_date, toDate:a.to_date }); break;

    // ── FOREVER ORDERS ──────────────────────────────────────────────────────
    case "create_forever_order":
      r = await POST("/forever/orders",{
        dhanClientId:CLIENT_ID, orderFlag:a.order_flag,
        transactionType:a.transaction_type, exchangeSegment:a.exchange_segment,
        productType:a.product_type, orderType:a.order_type, validity:a.validity,
        securityId:a.security_id, quantity:a.quantity, price:a.price,
        triggerPrice:a.trigger_price,
        ...(a.order_flag==="OCO"&&{price1:a.price1,triggerPrice1:a.trigger_price1,quantity1:a.quantity1}) }); break;
    case "modify_forever_order":
      r = await PUT(`/forever/orders/${a.order_id}`,{
        dhanClientId:CLIENT_ID, orderId:a.order_id, orderFlag:a.order_flag,
        orderType:a.order_type, legName:a.leg_name, quantity:a.quantity,
        price:a.price, triggerPrice:a.trigger_price, validity:a.validity }); break;
    case "cancel_forever_order": r = await DEL(`/forever/orders/${a.order_id}`); break;
    case "get_forever_orders":   r = await GET("/forever/orders"); break;

    // ── SUPER ORDERS ────────────────────────────────────────────────────────
    case "place_super_order":
      r = await POST("/super/orders",{
        dhanClientId:CLIENT_ID, correlationId:a.correlation_id??"",
        transactionType:a.transaction_type, exchangeSegment:a.exchange_segment,
        productType:a.product_type, orderType:a.order_type, securityId:a.security_id,
        quantity:a.quantity, price:a.price, targetPrice:a.target_price,
        stopLossPrice:a.stop_loss_price, trailingJump:a.trailing_jump??0 }); break;
    case "modify_super_order":
      r = await PUT(`/super/orders/${a.order_id}`,{
        dhanClientId:CLIENT_ID, orderId:a.order_id, legName:a.leg_name,
        ...(a.order_type&&{orderType:a.order_type}),
        ...(a.quantity&&{quantity:a.quantity}),
        ...(a.price&&{price:a.price}),
        ...(a.target_price&&{targetPrice:a.target_price}),
        ...(a.stop_loss_price&&{stopLossPrice:a.stop_loss_price}),
        ...(a.trailing_jump!=null&&{trailingJump:a.trailing_jump}) }); break;
    case "cancel_super_order": r = await DEL(`/super/orders/${a.order_id}/${a.order_leg}`); break;
    case "get_super_orders":   r = await GET("/super/orders"); break;

    // ── CONDITIONAL TRIGGERS ────────────────────────────────────────────────
    case "create_conditional_trigger":
      r = await POST("/alerts/orders",{
        dhanClientId:CLIENT_ID,
        condition:{
          comparisonType:a.comparison_type, exchangeSegment:a.exchange_segment,
          securityId:a.security_id,
          ...(a.indicator_name&&{indicatorName:a.indicator_name}),
          ...(a.time_frame&&{timeFrame:a.time_frame}),
          operator:a.operator,
          ...(a.comparing_value!=null&&{comparingValue:a.comparing_value}),
          ...(a.comparing_indicator&&{comparingIndicatorName:a.comparing_indicator}),
          expDate:a.exp_date, frequency:a.frequency, userNote:a.user_note??"" },
        orders:a.orders.map(o=>({
          transactionType:o.transaction_type, exchangeSegment:o.exchange_segment,
          productType:o.product_type, orderType:o.order_type, securityId:o.security_id,
          quantity:o.quantity, validity:o.validity, price:o.price,
          discQuantity:0, triggerPrice:o.trigger_price??0 })) }); break;
    case "get_all_triggers": r = await GET("/alerts/orders"); break;
    case "delete_trigger":   r = await DEL(`/alerts/orders/${a.alert_id}`); break;

    // ── TRADER'S CONTROL ────────────────────────────────────────────────────
    case "set_kill_switch":
      r = await POST(`/killswitch?killSwitchStatus=${a.status}`,{}); break;
    case "get_kill_switch":  r = await GET("/killswitch"); break;
    case "set_pnl_exit":
      r = await POST("/pnlExit",{
        profitValue:String(a.profit_value), lossValue:String(a.loss_value),
        productType:a.product_type, enableKillSwitch:a.enable_kill_switch??false }); break;
    case "get_pnl_exit":     r = await GET("/pnlExit"); break;
    case "stop_pnl_exit":    r = await DEL("/pnlExit"); break;

    // ── MARGIN CALCULATOR ───────────────────────────────────────────────────
    case "calculate_margin":
      r = await POST("/margincalculator",{
        dhanClientId:CLIENT_ID, securityId:a.security_id,
        exchangeSegment:a.exchange_segment, transactionType:a.transaction_type,
        quantity:a.quantity, productType:a.product_type, price:a.price,
        ...(a.trigger_price&&{triggerPrice:a.trigger_price}) }); break;
    case "calculate_margin_multi":
      r = await POST("/margincalculator/multi",{
        dhanClientId:CLIENT_ID,
        includePosition:a.include_positions??true,
        includeOrders:a.include_orders??true,
        scripList:a.orders.map(o=>({
          securityId:o.security_id, exchangeSegment:o.exchange_segment,
          transactionType:o.transaction_type, quantity:o.quantity,
          productType:o.product_type, price:o.price, triggerPrice:o.trigger_price??0 })) }); break;

    // ── LEDGER ──────────────────────────────────────────────────────────────
    case "get_ledger": r = await GET(`/ledger?from-date=${a.from_date}&to-date=${a.to_date}`); break;

    // ── OPTION CHAIN ────────────────────────────────────────────────────────
    case "get_option_chain":
      r = await POST("/optionchain",{
        UnderlyingScrip:Number(a.underlying_security_id),
        UnderlyingSeg:a.exchange_segment, Expiry:a.expiry_date }); break;
    case "get_expiry_dates":
      r = await POST("/optionchain/expirylist",{
        UnderlyingScrip:Number(a.underlying_security_id),
        UnderlyingSeg:a.exchange_segment, Instrument:a.instrument_type }); break;

    // ── P&L ANALYSIS (computed) ─────────────────────────────────────────────
    case "get_pnl_summary": {
      const [holdings, positions] = await Promise.all([GET("/holdings"), GET("/positions")]);
      const hr = (holdings||[]).map(h=>({
        symbol:h.tradingSymbol, qty:h.totalQty, avg:h.avgCostPrice, ltp:h.lastTradedPrice,
        invested:+(h.avgCostPrice*h.totalQty).toFixed(2),
        current:+(h.lastTradedPrice*h.totalQty).toFixed(2),
        pnl:+((h.lastTradedPrice-h.avgCostPrice)*h.totalQty).toFixed(2),
        pnl_pct:h.avgCostPrice>0?+(((h.lastTradedPrice-h.avgCostPrice)/h.avgCostPrice)*100).toFixed(2):0 }));
      const ti=hr.reduce((s,x)=>s+x.invested,0), tc=hr.reduce((s,x)=>s+x.current,0);
      const pr=(positions||[]).map(p=>({
        symbol:p.tradingSymbol, product:p.productType, qty:p.netQty,
        realized_pnl:+p.realizedProfit, unrealized_pnl:+(p.unrealizedProfit??0) }));
      r={ summary:{
        total_invested:+ti.toFixed(2), total_current_value:+tc.toFixed(2),
        holding_pnl:+(tc-ti).toFixed(2),
        holding_pnl_pct:ti>0?+(((tc-ti)/ti)*100).toFixed(2):0,
        position_realized_pnl:+pr.reduce((s,x)=>s+x.realized_pnl,0).toFixed(2),
        position_unrealized_pnl:+pr.reduce((s,x)=>s+x.unrealized_pnl,0).toFixed(2) },
        holdings:hr, positions:pr };
      break; }

    case "get_trade_pnl": {
      const trades = await GET(`/trades/${a.from_date}/${a.to_date}/0`);
      const g={};
      for(const t of (trades||[])){
        if(!g[t.tradingSymbol]) g[t.tradingSymbol]={symbol:t.tradingSymbol,buy_qty:0,buy_val:0,sell_qty:0,sell_val:0};
        if(t.transactionType==="BUY"){g[t.tradingSymbol].buy_qty+=t.tradedQuantity;g[t.tradingSymbol].buy_val+=t.tradedQuantity*t.tradedPrice;}
        else{g[t.tradingSymbol].sell_qty+=t.tradedQuantity;g[t.tradingSymbol].sell_val+=t.tradedQuantity*t.tradedPrice;} }
      const rows=Object.values(g).map(x=>({...x,realized_pnl:+(x.sell_val-x.buy_val).toFixed(2)}));
      r={from:a.from_date,to:a.to_date,
        total_realized_pnl:+rows.reduce((s,x)=>s+x.realized_pnl,0).toFixed(2), trades:rows};
      break; }

    default: throw new Error(`Unknown tool: ${name}`);
    }
    return { content:[{ type:"text", text:JSON.stringify(r,null,2) }] };
  } catch(err) {
    return { content:[{ type:"text", text:`Error: ${err.message}` }], isError:true };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("Dhan MCP Server v3.0 — 33 tools ready");
