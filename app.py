import streamlit as st
import streamlit.components.v1 as components
import sqlite3, json, math, random, urllib.parse, urllib.request, xml.etree.ElementTree as ET, re, html
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import deque, defaultdict
import pandas as pd

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / 'chaplife.db'

st.set_page_config(page_title='ChapLife', page_icon='✨', layout='wide', initial_sidebar_state='collapsed')

st.markdown('''
<style>
#MainMenu, footer, header {visibility:hidden;}
.block-container {padding-top:.8rem; padding-bottom:3rem; max-width:1180px;}
[data-testid="stSidebar"] {display:none;}
.hero {padding:1.05rem 1.2rem; border:1px solid rgba(120,120,120,.25); border-radius:22px; margin-bottom:.9rem;}
.hero h1 {margin:0; font-size:2rem;}
.hero p {margin:.3rem 0 0; opacity:.78;}
.bigcard {border:1px solid rgba(120,120,120,.25); border-radius:18px; padding:.9rem; min-height:116px;}
.smallmuted {opacity:.68; font-size:.9rem;}
.stButton>button {border-radius:14px; min-height:46px; font-weight:650;}
div[data-testid="stHorizontalBlock"] {gap:.65rem;}
.jugwrap {padding:.55rem; border-radius:20px; border:2px solid transparent; transition:.2s ease;}
.jugwrap.selected {border-color:#76a9ff; box-shadow:0 0 0 3px rgba(118,169,255,.24), 0 0 20px rgba(118,169,255,.35);}
.jug {height:210px; border:4px solid currentColor; border-top:none; border-radius:0 0 20px 20px; position:relative; overflow:hidden; margin:0 auto; max-width:155px;}
.water {position:absolute; left:0; right:0; bottom:0; background:rgba(70,140,220,.38); transition:height .25s ease;}
.juglabel {text-align:center; font-weight:750; margin-top:.4rem;}
.recipe {border-left:4px solid rgba(120,120,120,.4); padding-left:.85rem; margin:.3rem 0 1rem;}
@media (max-width: 640px){
  .block-container {padding-left:.7rem; padding-right:.7rem;}
  .hero h1 {font-size:1.65rem;}
  .jug {height:165px; max-width:115px;}
  .bigcard {min-height:100px;}
}
</style>
''', unsafe_allow_html=True)

# ---------- DB ----------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c=db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS finance_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_date TEXT, amount REAL, tx_type TEXT, category TEXT, subcategory TEXT, need_want TEXT, merchant TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS paychecks (id INTEGER PRIMARY KEY AUTOINCREMENT, pay_date TEXT, expected REAL, actual REAL, note TEXT);
    CREATE TABLE IF NOT EXISTS bills (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, amount REAL, due_day INTEGER, category TEXT, autopay INTEGER, note TEXT);
    CREATE TABLE IF NOT EXISTS savings_goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, goal_type TEXT, target_amount REAL, current_amount REAL, target_date TEXT, priority TEXT, contribution_frequency TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS savings_contributions (id INTEGER PRIMARY KEY AUTOINCREMENT, goal_id INTEGER, contrib_date TEXT, amount REAL, note TEXT);
    CREATE TABLE IF NOT EXISTS debts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, balance REAL, apr REAL, min_payment REAL, due_day INTEGER, note TEXT);
    CREATE TABLE IF NOT EXISTS roommate_payments (id INTEGER PRIMARY KEY AUTOINCREMENT, received_date TEXT, total_amount REAL, note TEXT);
    CREATE TABLE IF NOT EXISTS roommate_allocations (id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id INTEGER, category TEXT, detail TEXT, amount REAL);
    CREATE TABLE IF NOT EXISTS roommate_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_date TEXT, action TEXT, amount REAL, note TEXT);
    CREATE TABLE IF NOT EXISTS bill_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, household_total REAL, my_share REAL, roommate_share REAL, due_date TEXT, category TEXT, split_method TEXT, split_count INTEGER, custom_split TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS bill_funding (id INTEGER PRIMARY KEY AUTOINCREMENT, bill_plan_id INTEGER, fund_date TEXT, amount REAL, source TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS meals (id INTEGER PRIMARY KEY AUTOINCREMENT, meal_date TEXT, meal_type TEXT, meal_name TEXT, calories REAL, protein REAL, source TEXT, place TEXT, rating TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS grocery_items (id INTEGER PRIMARY KEY AUTOINCREMENT, week_of TEXT, item TEXT, category TEXT, qty TEXT, estimated_cost REAL, purchased INTEGER, note TEXT);
    CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_date TEXT, name TEXT, minutes INTEGER, intensity TEXT, focus TEXT, completed INTEGER, note TEXT);
    CREATE TABLE IF NOT EXISTS water_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, ounces REAL);
    CREATE TABLE IF NOT EXISTS vocab_progress (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, status TEXT, saved_date TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS growth_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, area TEXT, activity TEXT, rating INTEGER, note TEXT);
    CREATE TABLE IF NOT EXISTS confidence_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, skill TEXT, challenge TEXT, before_score INTEGER, after_score INTEGER, note TEXT);
    CREATE TABLE IF NOT EXISTS career_log (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, scenario_id TEXT, mode TEXT, choice TEXT, score INTEGER, skill TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS career_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, task_key TEXT UNIQUE, title TEXT, area TEXT, priority TEXT, status TEXT, due_time TEXT, detail TEXT, completed_at TEXT);
    CREATE TABLE IF NOT EXISTS career_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, msg_key TEXT UNIQUE, sender TEXT, subject TEXT, body TEXT, received_time TEXT, read INTEGER DEFAULT 0, flagged INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS career_sent (id INTEGER PRIMARY KEY AUTOINCREMENT, sent_time TEXT, recipient TEXT, cc TEXT, subject TEXT, body TEXT);
    CREATE TABLE IF NOT EXISTS career_reaction_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_sent_id INTEGER,
        due_minute INTEGER,
        sender TEXT,
        subject TEXT,
        body TEXT,
        reaction_type TEXT,
        task_key TEXT,
        task_title TEXT,
        task_area TEXT,
        task_priority TEXT,
        task_due_time TEXT,
        task_detail TEXT
    );
    CREATE TABLE IF NOT EXISTS career_activity (id INTEGER PRIMARY KEY AUTOINCREMENT, activity_time TEXT, activity_type TEXT, title TEXT, detail TEXT);
    CREATE TABLE IF NOT EXISTS career_rfis (id INTEGER PRIMARY KEY AUTOINCREMENT, rfi_no TEXT, subject TEXT, drawing_ref TEXT, question TEXT, impact TEXT, status TEXT, submitted_time TEXT, response TEXT);
    CREATE TABLE IF NOT EXISTS career_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, note TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS health_daily (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT UNIQUE, steps INTEGER, active_calories REAL, total_calories REAL, avg_hr REAL, resting_hr REAL, active_minutes REAL, sleep_hours REAL, source TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS cycle_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, period_status TEXT, flow TEXT, cramps TEXT, mood TEXT, energy TEXT, symptoms TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS medicines (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, brand TEXT, med_type TEXT, strength TEXT, serving TEXT, directions TEXT, reason TEXT, start_date TEXT, end_date TEXT, with_food TEXT, active INTEGER DEFAULT 1, label_notes TEXT);
    CREATE TABLE IF NOT EXISTS medicine_nutrients (id INTEGER PRIMARY KEY AUTOINCREMENT, medicine_id INTEGER, nutrient TEXT, amount REAL, unit TEXT, daily_value TEXT, source_text TEXT);
    CREATE TABLE IF NOT EXISTS medicine_doses (id INTEGER PRIMARY KEY AUTOINCREMENT, medicine_id INTEGER, dose_date TEXT, dose_time TEXT, status TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS health_imports (id INTEGER PRIMARY KEY AUTOINCREMENT, import_date TEXT, import_type TEXT, filename TEXT, extracted_text TEXT, confirmed INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS calendar_planning (id INTEGER PRIMARY KEY AUTOINCREMENT, event_date TEXT, event_title TEXT, start_time TEXT, end_time TEXT, planning_effect TEXT, ignore_event INTEGER DEFAULT 0, source TEXT);
    ''')
    c.commit(); c.close()

def get_setting(key, default=None):
    c=db(); r=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone(); c.close()
    if not r: return default
    try: return json.loads(r['value'])
    except Exception: return r['value']

def set_setting(key, value):
    c=db(); c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',(key,json.dumps(value))); c.commit(); c.close()

def rows(sql, params=()):
    c=db(); out=c.execute(sql,params).fetchall(); c.close(); return out

def execute(sql, params=()):
    c=db(); cur=c.execute(sql,params); c.commit(); lid=cur.lastrowid; c.close(); return lid

def delete_row(table, row_id): execute(f'DELETE FROM {table} WHERE id=?',(row_id,))

def reset_table(table): execute(f'DELETE FROM {table}')

def df_from(query, params=()):
    rs=rows(query,params)
    return pd.DataFrame([dict(r) for r in rs]) if rs else pd.DataFrame()

init_db()

# ---------- Helpers ----------
def money(x):
    try: return f'${float(x):,.2f}'
    except: return '$0.00'

def safe_float(x):
    try: return float(x)
    except: return 0.0

def payday_count(start, target, freq):
    if target <= start: return 1
    days=(target-start).days
    return max(1, {'Weekly':math.ceil(days/7),'Biweekly':math.ceil(days/14),'Twice Monthly':math.ceil(days/15.21875),'Monthly':math.ceil(days/30.4375)}.get(freq,math.ceil(days/14)))

def delete_reset_panel(table, label, display_col=None):
    data=rows(f'SELECT * FROM {table} ORDER BY id DESC')
    with st.expander(f'🗑️ Delete / reset {label}'):
        if data:
            opts={f"#{r['id']} — {r[display_col] if display_col and display_col in r.keys() else 'record'}":r['id'] for r in data}
            pick=st.selectbox('Delete one',list(opts.keys()),key=f'delpick_{table}')
            if st.button('Delete selected',key=f'del_{table}'):
                delete_row(table,opts[pick]); st.rerun()
        confirm=st.checkbox(f'I understand this clears all {label}',key=f'confirm_{table}')
        if st.button(f'Reset all {label}',key=f'reset_{table}',disabled=not confirm):
            reset_table(table); st.rerun()

# ---------- Navigation ----------
if 'page' not in st.session_state: st.session_state.page='Home'
def goto(p): st.session_state.page=p

pages = {
 'Home':'🏠', 'Finances':'💰', 'Food & Nutrition':'🥗', 'Grocery Shopping':'🛒', 'My Trainer':'🏋🏾‍♀️',
 'Water & Jug Puzzles':'💧', 'Vocabulary':'📖', 'Growth Lab':'🌱', 'Conversation & Current Events':'💬', 'Health & Life':'❤️', 'Career Simulator':'🏗️', 'My Progress':'📈', 'Settings':'⚙️'
}

nav_items=list(pages.items())
for start in range(0,len(nav_items),5):
    cc=st.columns(min(5,len(nav_items[start:start+5])))
    for i,(p,ic) in enumerate(nav_items[start:start+5]):
        if cc[i].button(f'{ic} {p}',use_container_width=True,key='nav_'+p): goto(p); st.rerun()

# ---------- Home ----------

def _dashboard_insights():
    today=date.today()
    t=today.isoformat()
    week=(today-timedelta(days=7)).isoformat()
    month=(today-timedelta(days=30)).isoformat()

    # Finance
    tx=rows("SELECT * FROM finance_transactions WHERE tx_date>=?",(month,))
    exp=sum((r["amount"] or 0) for r in tx if r["tx_type"]=="Expense")
    goals=rows("SELECT * FROM savings_goals")
    funded=sum((r["current_amount"] or 0) for r in goals)
    finance=[
        f"✅ {len(goals)} savings goal{'s' if len(goals)!=1 else ''} being tracked" if goals else "✅ Finance tracking is ready",
        f"✅ {money(funded)} saved toward goals" if funded>0 else "✅ Bill and paycheck tools are set up",
        f"🔧 Review this month's {money(exp)} spending" if exp>0 else "🔧 Log a few transactions for a spending insight"
    ]

    # Food
    meals=rows("SELECT * FROM meals WHERE meal_date>=?",(week,))
    eaten=[r for r in meals if r["eaten"]]
    food=[
        f"✅ {len(eaten)} planned meal{'s' if len(eaten)!=1 else ''} completed this week" if meals else "✅ Meal planner is ready",
        f"✅ {len(meals)} meal{'s' if len(meals)!=1 else ''} on your recent plan" if meals else "✅ Recipes can build your shopping list",
        "🔧 Complete/check off more planned meals" if meals and len(eaten)<len(meals) else "🔧 Build your next simple meal plan"
    ]

    # Grocery
    groceries=rows("SELECT * FROM grocery_items")
    checked=[r for r in groceries if r["checked"]]
    grocery=[
        f"✅ {len(groceries)} grocery item{'s' if len(groceries)!=1 else ''} currently tracked" if groceries else "✅ Grocery list is ready",
        f"✅ {len(checked)} item{'s' if len(checked)!=1 else ''} checked off" if checked else "✅ Meal ingredients can populate automatically",
        "🔧 Check store/quantity before shopping" if groceries else "🔧 Generate a list from your meal plan"
    ]

    # Trainer
    w=rows("SELECT * FROM workouts WHERE workout_date>=?",(week,))
    complete=[r for r in w if r["completed"]]
    trainer=[
        f"✅ {len(complete)} workout{'s' if len(complete)!=1 else ''} completed in 7 days" if complete else "✅ Personalized workout builder is ready",
        "✅ Workout history is being saved" if w else "✅ Routines can match your time and equipment",
        "🔧 Aim for one more completed workout" if complete else "🔧 Complete your first workout this week"
    ]

    # Water / jugs
    water=sum((r["ounces"] or 0) for r in rows("SELECT ounces FROM water_log WHERE log_date=?",(t,)))
    goal=safe_float(get_setting("water_goal",64))
    passed=set(get_setting("jug_passed",[]) or [])
    wateri=[
        f"✅ {water:.0f} oz logged today" if water else "✅ Daily water tracking is ready",
        f"✅ {len(passed)} jug level{'s' if len(passed)!=1 else ''} passed" if passed else "✅ 120 jug levels are available",
        f"🔧 {max(0,goal-water):.0f} oz left to reach today's goal" if water<goal else "🔧 Keep your hydration streak going"
    ]

    # Vocabulary
    vp=rows("SELECT * FROM vocab_progress")
    learned=[r for r in vp if r["learned"]]
    vocab=[
        f"✅ {len(learned)} word{'s' if len(learned)!=1 else ''} marked learned" if learned else "✅ Pronunciation practice is ready",
        f"✅ {len(vp)} vocabulary entr{'ies' if len(vp)!=1 else 'y'} practiced" if vp else "✅ Recall and sentence practice are available",
        "🔧 Practice one word in your own sentence today"
    ]

    # Growth
    gl=rows("SELECT * FROM growth_log WHERE log_date>=?",(week,))
    growth=[
        f"✅ {len(gl)} growth practice entr{'ies' if len(gl)!=1 else 'y'} this week" if gl else "✅ Daily advice is available",
        "✅ Completed practice can guide the next exercise" if gl else "✅ Exercises and examples are ready",
        "🔧 Complete one practice so ChapLife can adapt the next one"
    ]

    # Conversation
    cl=rows("SELECT * FROM confidence_log WHERE log_date>=?",(week,))
    convo=[
        f"✅ {len(cl)} conversation practice entr{'ies' if len(cl)!=1 else 'y'} this week" if cl else "✅ Conversation practice is ready",
        "✅ Current-events and social scenarios are available",
        "🔧 Practice adding a thought + follow-up question"
    ]

    # Career
    ca=rows("SELECT * FROM career_activity")
    accepted=sum(1 for r in ca if r["activity_type"] in ("RFI","Email","Cost Review","Meeting"))
    returned=sum(1 for r in ca if "returned" in (r["title"] or "").lower())
    career=[
        f"✅ {accepted} project action{'s' if accepted!=1 else ''} logged" if accepted else "✅ Full Project Coordinator workspace is ready",
        "✅ Training Library and examples stay available",
        f"🔧 Review {returned} returned item{'s' if returned!=1 else ''}" if returned else "🔧 Keep practicing follow-up and documentation"
    ]

    # Health
    hd=rows("SELECT * FROM health_daily WHERE log_date>=?",(week,))
    doses=rows("SELECT * FROM medicine_doses WHERE dose_date>=?",(week,))
    health=[
        f"✅ {len(hd)} health day{'s' if len(hd)!=1 else ''} logged this week" if hd else "✅ Samsung Health import is ready",
        f"✅ {len(doses)} medicine/supplement dose{'s' if len(doses)!=1 else ''} logged" if doses else "✅ Medicine, vitamin and cycle trackers are ready",
        "🔧 Log consistently so patterns become more useful"
    ]

    return {
        "Finances":finance,"Food & Nutrition":food,"Grocery Shopping":grocery,
        "My Trainer":trainer,"Water & Jug Puzzles":wateri,"Vocabulary":vocab,
        "Growth Lab":growth,"Conversation & Current Events":convo,
        "Career Simulator":career,"Health & Life":health
    }

def home():
    st.markdown('<div class="hero"><h1>✨ ChapLife</h1><p>Track it • save it • see your progress • build a healthier, stronger life.</p></div>',unsafe_allow_html=True)

    today=date.today().isoformat()
    water=sum(r['ounces'] for r in rows('SELECT ounces FROM water_log WHERE log_date=?',(today,)))
    water_goal=safe_float(get_setting('water_goal',64))
    savings=sum(r['current_amount'] for r in rows('SELECT current_amount FROM savings_goals'))
    workouts=rows("SELECT COUNT(*) n FROM workouts WHERE completed=1 AND workout_date>=?",((date.today()-timedelta(days=7)).isoformat(),))[0]['n']
    calories=sum(r['calories'] or 0 for r in rows('SELECT calories FROM meals WHERE meal_date=?',(today,)))
    c=st.columns(4)
    c[0].metric('Water today',f'{water:.0f} oz',f'Goal {water_goal:.0f} oz')
    c[1].metric('Saved toward goals',money(savings))
    c[2].metric('Workouts / 7 days',workouts)
    c[3].metric('Calories logged',f'{calories:.0f}')

    st.subheader('My dashboard')
    insights=_dashboard_insights()
    grid=[
        ('💰','Finances'),('🥗','Food & Nutrition'),('🛒','Grocery Shopping'),
        ('🏋🏾‍♀️','My Trainer'),('💧','Water & Jug Puzzles'),('📖','Vocabulary'),
        ('🌱','Growth Lab'),('💬','Conversation & Current Events'),('🏗️','Career Simulator'),
        ('❤️','Health & Life')
    ]

    st.markdown("""
    <style>
    [class*="st-key-dashcard_"] button{
        min-height:188px!important;
        border-radius:20px!important;
        padding:1rem!important;
        text-align:left!important;
        justify-content:flex-start!important;
        white-space:pre-wrap!important;
        line-height:1.45!important;
        border:1px solid rgba(120,120,120,.28)!important;
    }
    .st-key-progresshome button{
        min-height:72px!important;
        border-radius:18px!important;
        font-size:1.05rem!important;
        font-weight:750!important;
    }
    @media(max-width:640px){
      [class*="st-key-dashcard_"] button{min-height:170px!important;padding:.8rem!important;}
    }
    </style>
    """,unsafe_allow_html=True)

    for rowstart in range(0,len(grid),2):
        cc=st.columns(2)
        for j,(ic,p) in enumerate(grid[rowstart:rowstart+2]):
            lines=insights[p]
            label=f"{ic}  {p}\n\n{lines[0]}\n{lines[1]}\n{lines[2]}\n\nOpen →"
            with cc[j]:
                with st.container(key=f"dashcard_{rowstart}_{j}"):
                    if st.button(label,use_container_width=True,key="home_"+p):
                        goto(p); st.rerun()

    st.markdown("### Detailed progress")
    with st.container(key="progresshome"):
        if st.button("📈 Open My Progress — detailed trends for every area →",use_container_width=True,key="home_progress_detail"):
            goto("My Progress"); st.rerun()

# ---------- Finances ----------
def roommate_summary():
    hold=sum(r['amount'] for r in rows("SELECT amount FROM roommate_allocations WHERE category='Hold for Her'"))
    ledger=rows('SELECT action,amount FROM roommate_ledger')
    spent=sum(r['amount'] for r in ledger if r['action']=='Gave to Roommate / She Spent It')
    used=sum(r['amount'] for r in ledger if r['action']=='Used Temporarily')
    replaced=sum(r['amount'] for r in ledger if r['action']=='Replaced Money')
    balance=max(0,hold-spent)
    owed=max(0,used-replaced)
    return balance,owed,max(0,balance-owed)

def split_amounts(amount, method, custom=''):
    amount=max(0,float(amount or 0))
    counts={'Pay all from one paycheck':1,'Split in half':2,'Split into thirds':3,'Split into fourths':4}
    if method in counts:
        n=counts[method]; base=round(amount/n,2); vals=[base]*n
        vals[-1]=round(amount-sum(vals[:-1]),2)
        return vals
    vals=[]
    for part in re.split(r'[,;\\n]+',custom or ''):
        try:
            if part.strip(): vals.append(round(float(part.strip().replace('$','')),2))
        except: pass
    return vals

def finances():
    st.title('💰 Finances')
    tabs=st.tabs(['Overview','Paychecks','Bills & Spending','🏠 Shared Household','Bill Funding','Savings Planner','Debt','Import / Export'])

    with tabs[0]:
        tx=df_from('SELECT * FROM finance_transactions ORDER BY tx_date DESC')
        income=tx.loc[tx.tx_type=='Income','amount'].sum() if not tx.empty else 0
        expense=tx.loc[tx.tx_type=='Expense','amount'].sum() if not tx.empty else 0
        goals=df_from('SELECT * FROM savings_goals'); saved=goals.current_amount.sum() if not goals.empty else 0
        debts=df_from('SELECT * FROM debts'); debt_total=debts.balance.sum() if not debts.empty else 0
        held,owed,physical=roommate_summary()
        c=st.columns(5)
        c[0].metric('Income logged',money(income)); c[1].metric('Expenses logged',money(expense))
        c[2].metric('Savings goals',money(saved)); c[3].metric('Debt balance',money(debt_total))
        c[4].metric('Roommate money held',money(held),f'{money(owed)} to replace' if owed else 'Protected')
        if not tx.empty: st.dataframe(tx[['tx_date','merchant','category','tx_type','amount','need_want','note']].head(12),use_container_width=True,hide_index=True)

    with tabs[1]:
        with st.form('add_paycheck',clear_on_submit=True):
            c=st.columns(4); d=c[0].date_input('Pay date',date.today()); expected=c[1].number_input('Expected pay',min_value=0.0,step=50.0); actual=c[2].number_input('Actual pay',min_value=0.0,step=50.0); note=c[3].text_input('Note')
            if st.form_submit_button('Save paycheck',use_container_width=True):
                execute('INSERT INTO paychecks(pay_date,expected,actual,note) VALUES(?,?,?,?)',(d.isoformat(),expected,actual,note)); amt=actual or expected
                execute('INSERT INTO finance_transactions(tx_date,amount,tx_type,category,subcategory,need_want,merchant,note) VALUES(?,?,?,?,?,?,?,?)',(d.isoformat(),amt,'Income','Paycheck','Regular','Income','Paycheck',note)); st.rerun()
        pay=df_from('SELECT * FROM paychecks ORDER BY pay_date DESC')
        if not pay.empty: st.dataframe(pay,use_container_width=True,hide_index=True)
        delete_reset_panel('paychecks','paychecks','pay_date')

    with tabs[2]:
        with st.form('add_tx',clear_on_submit=True):
            c=st.columns(4); d=c[0].date_input('Date',date.today(),key='txdate'); typ=c[1].selectbox('Type',['Expense','Income','Transfer']); cat=c[2].selectbox('Category',['Housing','Utilities','Food','Groceries','Transportation','Debt','Savings','Personal','Entertainment','Medical','Gifts','Subscription','Travel','Other']); detail=c[3].text_input('Other category / detail')
            c=st.columns(4); amt=c[0].number_input('Amount',min_value=0.0,step=1.0); nw=c[1].selectbox('Classification',['Need','Want','Savings','Debt','Transfer','Income','Other']); merchant=c[2].text_input('Merchant / source'); note=c[3].text_input('Note')
            if st.form_submit_button('Save transaction',use_container_width=True):
                execute('INSERT INTO finance_transactions(tx_date,amount,tx_type,category,subcategory,need_want,merchant,note) VALUES(?,?,?,?,?,?,?,?)',(d.isoformat(),amt,typ,cat,detail,nw,merchant,note)); st.rerun()
        with st.form('billform',clear_on_submit=True):
            st.subheader('Simple recurring bills'); c=st.columns(5); n=c[0].text_input('Bill'); amt=c[1].number_input('Amount',min_value=0.0,step=1.0,key='billamt'); day=c[2].number_input('Due day',1,31,1); cat=c[3].selectbox('Bill category',['Housing','Utilities','Transportation','Debt','Subscription','Insurance','Medical','Other']); auto=c[4].selectbox('Autopay?',['No','Yes']); note=st.text_input('Bill note')
            if st.form_submit_button('Add bill'): execute('INSERT INTO bills(name,amount,due_day,category,autopay,note) VALUES(?,?,?,?,?,?)',(n,amt,day,cat,auto=='Yes',note)); st.rerun()
        b=df_from('SELECT * FROM bills ORDER BY due_day')
        if not b.empty: st.dataframe(b[['name','amount','due_day','category','autopay','note']],use_container_width=True,hide_index=True)
        delete_reset_panel('finance_transactions','transactions','merchant'); delete_reset_panel('bills','bills','name')

    with tabs[3]:
        st.subheader('🏠 Shared Household / Roommate Money')
        st.caption("Track what she gives you, what each part is for, and money you're holding for her without treating it as your income.")
        held,owed,physical=roommate_summary()
        c=st.columns(3); c[0].metric('Her held balance',money(held)); c[1].metric('I need to replace',money(owed)); c[2].metric('Held money currently available',money(physical))

        with st.form('roommate_payment',clear_on_submit=True):
            c=st.columns(3); rd=c[0].date_input('Date received',date.today(),key='rmdate'); total=c[1].number_input('Total she gave me',min_value=0.0,step=10.0); pnote=c[2].text_input('Payment note',placeholder='Cash, Zelle, etc.')
            st.markdown('**Allocate the payment**')
            allocs=[]
            for i in range(5):
                c=st.columns([1.2,1.6,1])
                cat=c[0].selectbox(f'Part {i+1}',['Rent','Utilities / Bills','Household','Hold for Her','Repayment','Other'],key=f'rmcat{i}')
                detail=c[1].text_input('Bill / detail',key=f'rmdetail{i}',placeholder='Rent, electric, internet…')
                a=c[2].number_input('Amount',min_value=0.0,step=10.0,key=f'rmamt{i}')
                if a>0: allocs.append((cat,detail,a))
            allocated=sum(x[2] for x in allocs); diff=round(total-allocated,2)
            if total>0: st.info(f'Allocated {money(allocated)} • Remaining {money(diff)}')
            if st.form_submit_button('Save roommate payment',use_container_width=True):
                if total<=0: st.error('Enter the amount she gave you.')
                elif abs(diff)>.009: st.error('The allocations must equal the total payment.')
                else:
                    pid=execute('INSERT INTO roommate_payments(received_date,total_amount,note) VALUES(?,?,?)',(rd.isoformat(),total,pnote))
                    for cat,detail,a in allocs: execute('INSERT INTO roommate_allocations(payment_id,category,detail,amount) VALUES(?,?,?,?)',(pid,cat,detail,a))
                    st.rerun()

        st.markdown('#### Her held-money ledger')
        action=st.selectbox('What happened?',['Used Temporarily','Replaced Money','Gave to Roommate / She Spent It'])
        c=st.columns(3); ld=c[0].date_input('Date',date.today(),key='ledgerdate'); la=c[1].number_input('Amount',min_value=0.0,step=10.0,key='ledgeramt'); ln=c[2].text_input('Note',key='ledgernote')
        if st.button('Save held-money activity',use_container_width=True):
            if la>0: execute('INSERT INTO roommate_ledger(tx_date,action,amount,note) VALUES(?,?,?,?)',(ld.isoformat(),action,la,ln)); st.rerun()

        pay=df_from('SELECT * FROM roommate_payments ORDER BY received_date DESC,id DESC')
        if not pay.empty: st.markdown('#### Payment history'); st.dataframe(pay,use_container_width=True,hide_index=True)
        alloc=df_from("SELECT p.received_date,a.category,a.detail,a.amount FROM roommate_allocations a JOIN roommate_payments p ON p.id=a.payment_id ORDER BY p.received_date DESC,a.id DESC")
        if not alloc.empty: st.markdown('#### Allocation history'); st.dataframe(alloc,use_container_width=True,hide_index=True)
        led=df_from('SELECT tx_date,action,amount,note FROM roommate_ledger ORDER BY tx_date DESC,id DESC')
        if not led.empty: st.markdown('#### Held-money history'); st.dataframe(led,use_container_width=True,hide_index=True)
        delete_reset_panel('roommate_ledger','held-money activity','action')
        with st.expander('🗑️ Reset roommate payment history'):
            ok=st.checkbox('I understand this clears roommate payments and allocations',key='reset_rm_pay')
            if st.button('Reset roommate payments',disabled=not ok):
                reset_table('roommate_allocations'); reset_table('roommate_payments'); st.rerun()

    with tabs[4]:
        st.subheader('📆 Bill Funding Across Paychecks')
        st.caption('Spread your share across one paycheck, halves, thirds, fourths, or your own custom amounts.')
        with st.form('bill_plan_form',clear_on_submit=True):
            c=st.columns(4); name=c[0].text_input('Bill / goal',placeholder='September Rent'); household=c[1].number_input('Whole household bill',min_value=0.0,step=50.0,value=2700.0); mine=c[2].number_input('My share',min_value=0.0,step=50.0,value=1800.0); roomie=c[3].number_input('Roommate share',min_value=0.0,step=50.0,value=900.0)
            c=st.columns(4); due=c[0].date_input('Due date',date.today()+timedelta(days=30)); cat=c[1].selectbox('Category',['Rent / Housing','Utilities','Insurance','Debt','Subscription','Travel','Other']); method=c[2].selectbox('Fund my share',['Pay all from one paycheck','Split in half','Split into thirds','Split into fourths','Custom split']); note=c[3].text_input('Other / note')
            custom=''
            if method=='Custom split': custom=st.text_input('Custom paycheck amounts',placeholder='700, 700, 400')
            vals=split_amounts(mine,method,custom)
            if vals: st.caption('Planned pieces: '+' • '.join(money(v) for v in vals)+f' = {money(sum(vals))}')
            if st.form_submit_button('Create bill funding plan',use_container_width=True):
                if not name: st.error('Give the bill a name.')
                elif abs((mine+roomie)-household)>.009: st.error('Your share + roommate share must equal the whole household bill.')
                elif method=='Custom split' and abs(sum(vals)-mine)>.009: st.error(f'Custom split totals {money(sum(vals))}; it must equal {money(mine)}.')
                else:
                    execute('INSERT INTO bill_plans(name,household_total,my_share,roommate_share,due_date,category,split_method,split_count,custom_split,note) VALUES(?,?,?,?,?,?,?,?,?,?)',(name,household,mine,roomie,due.isoformat(),cat,method,len(vals),custom,note)); st.rerun()

        for bp in rows('SELECT * FROM bill_plans ORDER BY due_date,id'):
            funded=sum(r['amount'] for r in rows('SELECT amount FROM bill_funding WHERE bill_plan_id=?',(bp['id'],)))
            remaining=max(0,bp['my_share']-funded); pct=min(1,funded/bp['my_share']) if bp['my_share'] else 0
            vals=split_amounts(bp['my_share'],bp['split_method'],bp['custom_split'] or '')
            with st.container(border=True):
                c=st.columns([2,1,1,1]); c[0].subheader(bp['name']); c[1].metric('Whole bill',money(bp['household_total'])); c[2].metric('My share',money(bp['my_share'])); c[3].metric('Roommate share',money(bp['roommate_share']))
                st.progress(pct); st.caption(f"{money(funded)} funded • {money(remaining)} remaining • due {bp['due_date']} • {bp['split_method']}")
                if vals: st.write('**Planned paycheck pieces:** '+' → '.join(money(v) for v in vals))
                c=st.columns([1,1,2]); add=c[0].number_input('Set aside now',min_value=0.0,step=10.0,key=f'fund{bp["id"]}'); source=c[1].selectbox('From',['Paycheck','Other income','Transfer','Other'],key=f'fundsrc{bp["id"]}'); fnote=c[2].text_input('Note',key=f'fundnote{bp["id"]}')
                if st.button('Add funding',key=f'addfund{bp["id"]}',use_container_width=True):
                    if add>0: execute('INSERT INTO bill_funding(bill_plan_id,fund_date,amount,source,note) VALUES(?,?,?,?,?)',(bp['id'],date.today().isoformat(),add,source,fnote)); st.rerun()
                hist=df_from('SELECT fund_date,amount,source,note FROM bill_funding WHERE bill_plan_id=? ORDER BY fund_date,id',(bp['id'],))
                if not hist.empty:
                    with st.expander('Funding history'): st.dataframe(hist,use_container_width=True,hide_index=True)
        delete_reset_panel('bill_funding','bill funding entries','source')
        with st.expander('🗑️ Delete / reset bill funding plans'):
            plans=rows('SELECT * FROM bill_plans ORDER BY id DESC')
            if plans:
                opts={f"#{r['id']} — {r['name']}":r['id'] for r in plans}; pick=st.selectbox('Delete one plan',list(opts.keys()),key='del_billplan')
                if st.button('Delete selected plan'):
                    pid=opts[pick]; execute('DELETE FROM bill_funding WHERE bill_plan_id=?',(pid,)); delete_row('bill_plans',pid); st.rerun()
            ok=st.checkbox('I understand this clears all bill funding plans',key='reset_billplans')
            if st.button('Reset all bill funding plans',disabled=not ok): reset_table('bill_funding'); reset_table('bill_plans'); st.rerun()

    with tabs[5]:
        st.subheader('Savings Planner'); st.caption('Create a goal and ChapLife calculates what you need to save by your deadline.')
        with st.form('goalform',clear_on_submit=True):
            c=st.columns(4); name=c[0].text_input('Goal name',placeholder='MLK Weekend 2027'); gtype=c[1].selectbox('Goal type',['Trip / Vacation','Emergency Fund','Car','Home','Event','Holiday','Major Purchase','Personal','Other']); target=c[2].number_input('Goal amount',min_value=1.0,step=50.0,value=3800.0); current=c[3].number_input('Already saved',min_value=0.0,step=25.0)
            c=st.columns(4); tdate=c[0].date_input('Need it by',date.today()+timedelta(days=180)); priority=c[1].selectbox('Priority',['High','Medium','Low']); freq=c[2].selectbox('Contribution schedule',['Weekly','Biweekly','Twice Monthly','Monthly']); note=c[3].text_input('Other / note')
            if st.form_submit_button('Create savings plan',use_container_width=True): execute('INSERT INTO savings_goals(name,goal_type,target_amount,current_amount,target_date,priority,contribution_frequency,note) VALUES(?,?,?,?,?,?,?,?)',(name,gtype,target,current,tdate.isoformat(),priority,freq,note)); st.rerun()
        for g in rows('SELECT * FROM savings_goals ORDER BY target_date'):
            target_date=datetime.strptime(g['target_date'],'%Y-%m-%d').date(); rem=max(0,g['target_amount']-g['current_amount']); n=payday_count(date.today(),target_date,g['contribution_frequency']); per=rem/n if n else rem; pct=min(1,g['current_amount']/g['target_amount']) if g['target_amount'] else 0
            with st.container(border=True):
                c=st.columns([2,1,1,1]); c[0].subheader(g['name']); c[1].metric('Goal',money(g['target_amount'])); c[2].metric('Saved',money(g['current_amount'])); c[3].metric('Needed / period',money(per)); st.progress(pct)
                st.caption(f"{pct*100:.0f}% complete • {money(rem)} remaining • target {target_date.strftime('%b %d, %Y')} • {n} contribution periods left")
                with st.expander('Add contribution / What-if'):
                    c=st.columns(2); add=c[0].number_input('Contribution',min_value=0.0,step=10.0,key=f'contrib{g["id"]}'); what=c[1].number_input('What if I save this each period?',min_value=0.0,step=10.0,key=f'what{g["id"]}')
                    if add>0 and st.button('Add contribution',key=f'addc{g["id"]}'): execute('INSERT INTO savings_contributions(goal_id,contrib_date,amount,note) VALUES(?,?,?,?)',(g['id'],date.today().isoformat(),add,'')); execute('UPDATE savings_goals SET current_amount=current_amount+? WHERE id=?',(add,g['id'])); st.rerun()
                    if what>0: st.info(f'At {money(what)} per {g["contribution_frequency"].lower()} period: about {math.ceil(rem/what) if rem else 0} contributions.')
        delete_reset_panel('savings_goals','savings goals','name')

    with tabs[6]:
        with st.form('debtform',clear_on_submit=True):
            c=st.columns(5); n=c[0].text_input('Debt / card'); bal=c[1].number_input('Balance',min_value=0.0,step=50.0); apr=c[2].number_input('APR %',min_value=0.0,max_value=100.0,step=.1); mp=c[3].number_input('Minimum payment',min_value=0.0,step=10.0); dd=c[4].number_input('Due day',1,31,1,key='debtdue'); note=st.text_input('Debt note')
            if st.form_submit_button('Add debt'): execute('INSERT INTO debts(name,balance,apr,min_payment,due_day,note) VALUES(?,?,?,?,?,?)',(n,bal,apr,mp,dd,note)); st.rerun()
        d=df_from('SELECT * FROM debts ORDER BY apr DESC')
        if not d.empty: st.dataframe(d,use_container_width=True,hide_index=True)
        delete_reset_panel('debts','debts','name')

    with tabs[7]:
        st.caption('Import transaction history from CSV.'); up=st.file_uploader('Import CSV',type=['csv'])
        if up: st.dataframe(pd.read_csv(up).head(),use_container_width=True)
        tx=df_from('SELECT * FROM finance_transactions ORDER BY tx_date')
        if not tx.empty: st.download_button('Download transactions CSV',tx.to_csv(index=False).encode(),'chaplife_transactions.csv','text/csv')

# ---------- Meals / recipes ----------
MEALS=[
 {'name':'Egg & avocado toast with berries','type':'Breakfast','cal':390,'protein':20,'goal':['Lose weight','General health','Maintain weight'],'ingredients':[('Eggs','Dairy / Eggs',2,'each','Buy 1 half-dozen or dozen'),('Whole-grain bread','Pantry',2,'slices','1 loaf'),('Avocado','Produce',0.5,'each','1 avocado covers 2 servings'),('Berries','Produce',1,'cup','1 pint ≈ 2 cups')],'steps':['Toast the bread.','Cook eggs to your preference.','Mash avocado over toast, top with eggs, and serve berries on the side.']},
 {'name':'Greek yogurt berry crunch','type':'Breakfast','cal':340,'protein':25,'goal':['Lose weight','Build strength / muscle','General health'],'ingredients':[('Plain Greek yogurt','Dairy / Eggs',1,'cup','32 oz tub ≈ 4 cups'),('Berries','Produce',1,'cup','1 pint ≈ 2 cups'),('Granola','Pantry',0.25,'cup','11–12 oz bag'),('Honey','Pantry',1,'tsp','Small bottle')],'steps':['Add yogurt to a bowl.','Top with berries and granola.','Drizzle with honey.']},
 {'name':'Chicken veggie wrap','type':'Lunch','cal':480,'protein':40,'goal':['Lose weight','Build strength / muscle','General health'],'ingredients':[('Chicken breast','Meat / Protein',5,'oz','Buy raw weight; 1 lb = 16 oz'),('Whole-wheat tortilla','Pantry',1,'each','8-count pack'),('Salad mix','Produce',2,'cups','5 oz bag ≈ 4–5 cups'),('Tomato','Produce',0.5,'each','1 tomato covers ~2 wraps'),('Light dressing','Pantry',2,'tbsp','Small bottle')],'steps':['Season and cook chicken; slice thinly.','Warm tortilla for 10–15 seconds.','Add salad mix, tomato, chicken and dressing; roll tightly.']},
 {'name':'Turkey hummus sandwich + apple','type':'Lunch','cal':450,'protein':33,'goal':['Lose weight','General health','Maintain weight'],'ingredients':[('Deli turkey','Meat / Protein',4,'oz','8 oz pack = 2 servings'),('Whole-grain bread','Pantry',2,'slices','1 loaf'),('Hummus','Dairy / Eggs',2,'tbsp','8 oz tub'),('Spinach','Produce',1,'cup','5 oz bag'),('Apple','Produce',1,'each','Buy per serving')],'steps':['Spread hummus on bread.','Layer turkey and spinach.','Serve with apple.']},
 {'name':'Chicken rice veggie bowl','type':'Dinner','cal':570,'protein':46,'goal':['Build strength / muscle','General health','Maintain weight'],'ingredients':[('Chicken breast','Meat / Protein',6,'oz','Buy raw weight; 1 lb = 16 oz'),('Brown rice, dry','Pantry',0.25,'cup','1 cup dry ≈ 3 cups cooked'),('Frozen mixed vegetables','Frozen',2,'cups','12 oz bag ≈ 3 cups'),('Low-sodium sauce','Pantry',1,'tbsp','Small bottle')],'steps':['Cook rice according to package directions.','Season and cook chicken, then slice.','Heat vegetables.','Layer rice, vegetables and chicken; finish with sauce.']},
 {'name':'Turkey taco bowls','type':'Dinner','cal':530,'protein':41,'goal':['Lose weight','Build strength / muscle','General health'],'ingredients':[('Lean ground turkey','Meat / Protein',6,'oz','1 lb = about 2.7 servings'),('Brown rice, dry','Pantry',0.2,'cup','1 cup dry ≈ 3 cups cooked'),('Romaine lettuce','Produce',1,'cup','1 head ≈ 6 cups'),('Salsa','Pantry',0.25,'cup','16 oz jar ≈ 2 cups'),('Shredded cheese','Dairy / Eggs',1,'oz','8 oz bag = 8 servings')],'steps':['Brown turkey with taco seasoning.','Cook rice.','Add lettuce and rice to bowl, then turkey.','Top with salsa and cheese.']},
 {'name':'Sheet-pan salmon, potato & broccoli','type':'Dinner','cal':600,'protein':44,'goal':['General health','Build strength / muscle','Maintain weight'],'ingredients':[('Salmon fillet','Meat / Protein',6,'oz','Buy 6 oz per serving'),('Baby potatoes','Produce',8,'oz','1.5 lb bag = 3 servings'),('Broccoli florets','Produce',2,'cups','12 oz bag ≈ 4 cups'),('Olive oil','Pantry',2,'tsp','Pantry staple')],'steps':['Heat oven to 425°F.','Halve potatoes, toss with 1 tsp oil and roast 15 minutes.','Add salmon and broccoli with remaining oil and seasoning.','Roast 12–15 minutes more until salmon is cooked through.']},
 {'name':'Chicken pasta primavera','type':'Dinner','cal':590,'protein':43,'goal':['Build strength / muscle','Maintain weight','General health'],'ingredients':[('Chicken breast','Meat / Protein',5,'oz','Buy raw weight'),('Whole-wheat pasta, dry','Pantry',2,'oz','1 lb box = 8 servings'),('Frozen mixed vegetables','Frozen',1.5,'cups','12 oz bag ≈ 3 cups'),('Marinara sauce','Pantry',0.5,'cup','24 oz jar ≈ 3 cups')],'steps':['Cook pasta.','Cook seasoned chicken and slice.','Heat vegetables and marinara.','Toss pasta, vegetables and sauce; top with chicken.']},
 {'name':'Protein snack plate','type':'Snack','cal':270,'protein':21,'goal':['Lose weight','Build strength / muscle','General health'],'ingredients':[('String cheese','Dairy / Eggs',1,'each','6–12 pack'),('Deli turkey','Meat / Protein',2,'oz','8 oz pack = 4 snack servings'),('Apple','Produce',1,'each','Buy per serving')],'steps':['Slice apple if desired.','Arrange turkey and cheese with apple.']},
 {'name':'Peanut butter banana oatmeal','type':'Breakfast','cal':420,'protein':16,'goal':['Build strength / muscle','Maintain weight','General health'],'ingredients':[('Old-fashioned oats','Pantry',0.5,'cup','18 oz canister ≈ 13 servings'),('Milk','Dairy / Eggs',1,'cup','Half gallon = 8 cups'),('Banana','Produce',1,'each','Buy per serving'),('Peanut butter','Pantry',1,'tbsp','16 oz jar')],'steps':['Cook oats with milk.','Slice banana over oats.','Swirl in peanut butter.']},
]

def meal_pool(meal_type,goal):
    pool=[m for m in MEALS if m['type']==meal_type and (goal in m['goal'] or goal=='Other')]
    return pool or [m for m in MEALS if m['type']==meal_type]

def aggregate_ingredients(plan):
    agg={}
    for d,ms in plan.items():
        for m in ms:
            for item,cat,qty,unit,buy in m['ingredients']:
                k=(item,cat,unit,buy); agg[k]=agg.get(k,0)+qty
    return agg

def fmt_qty(q):
    if abs(q-round(q))<1e-8: return str(int(round(q)))
    return f'{q:.2f}'.rstrip('0').rstrip('.')

def save_plan_grocery(plan):
    week=date.today()-timedelta(days=date.today().weekday()); execute('DELETE FROM grocery_items WHERE week_of=?',(week.isoformat(),))
    for (item,cat,unit,buy),qty in aggregate_ingredients(plan).items():
        execute('INSERT INTO grocery_items(week_of,item,category,qty,estimated_cost,purchased,note) VALUES(?,?,?,?,?,?,?)',(week.isoformat(),item,cat,f'{fmt_qty(qty)} {unit}',0,0,buy))

def food():
    st.title('🥗 Food & Nutrition')
    tabs=st.tabs(['Lifestyle Profile','Plan My Week','Today / Meal Counter','Eating Out'])
    with tabs[0]:
        prof=get_setting('food_profile',{}) or {}
        with st.form('foodprof'):
            c=st.columns(3); goal=c[0].selectbox('Main goal',['Lose weight','Maintain weight','Build strength / muscle','Eat more consistently','General health','Other'],index=['Lose weight','Maintain weight','Build strength / muscle','Eat more consistently','General health','Other'].index(prof.get('goal','General health')) if prof.get('goal') in ['Lose weight','Maintain weight','Build strength / muscle','Eat more consistently','General health','Other'] else 4); cook=c[1].selectbox('Cooking style',['Very simple','Simple','Moderate','I like cooking']); cooktime=c[2].selectbox('Typical cook time',['10–15 minutes','20–30 minutes','30–45 minutes','Flexible'])
            c=st.columns(3); mealsper=c[0].selectbox('Meals per day',[2,3,4,5],index=1); eatout=c[1].selectbox('How often do you eat out?',['Rarely','1–2x/week','3–4x/week','Most days']); budget=c[2].number_input('Weekly grocery budget',min_value=0.0,step=10.0,value=float(prof.get('budget',100)))
            calorie_target=st.number_input('Optional daily calorie target for your counter (0 = no target)',min_value=0,max_value=5000,step=50,value=int(prof.get('calorie_target',0) or 0))
            dislikes=st.text_area('Foods you dislike / avoid',value=prof.get('dislikes','')); lifestyle=st.text_area('Lifestyle notes',placeholder='Packable lunches, leftovers, eating out Saturday, etc.',value=prof.get('lifestyle',''))
            if st.form_submit_button('Save lifestyle profile',use_container_width=True): set_setting('food_profile',{'goal':goal,'cook':cook,'time':cooktime,'meals':mealsper,'eatout':eatout,'budget':budget,'calorie_target':calorie_target,'dislikes':dislikes,'lifestyle':lifestyle}); st.rerun()
    with tabs[1]:
        prof=get_setting('food_profile',{}) or {}; goal=prof.get('goal','General health')
        st.caption(f'Planning style: simple meals • goal: {goal}. Every meal includes a recipe and exact ingredient amounts.')
        days=st.multiselect('Days to plan',['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],default=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
        c=st.columns(2)
        if c[0].button('Build simple weekly plan',use_container_width=True):
            plan={}
            for d in days:
                plan[d]=[random.choice(meal_pool('Breakfast',goal)),random.choice(meal_pool('Lunch',goal)),random.choice(meal_pool('Dinner',goal)),random.choice(meal_pool('Snack',goal))]
            st.session_state.meal_plan=plan; set_setting('meal_plan',plan); save_plan_grocery(plan); st.rerun()
        if c[1].button('Clear meal plan',use_container_width=True): st.session_state.pop('meal_plan',None); set_setting('meal_plan',{}); st.rerun()
        plan=st.session_state.get('meal_plan') or get_setting('meal_plan',{})
        if plan:
            st.session_state.meal_plan=plan
            for d,ms in plan.items():
                st.subheader(d)
                for i,m in enumerate(ms):
                    with st.expander(f"{m['type']} • {m['name']} — {m['cal']} cal • {m['protein']}g protein"):
                        st.markdown('**Ingredients — 1 serving**')
                        for item,cat,qty,unit,buy in m['ingredients']: st.write(f'• {item}: **{fmt_qty(qty)} {unit}**')
                        st.markdown('**Simple recipe**')
                        for n,step in enumerate(m['steps'],1): st.write(f'{n}. {step}')
                        key=f"done_{d}_{i}_{m['name']}"
                        if st.button('✅ I ate this — add to today’s counter',key=key,use_container_width=True):
                            execute('INSERT INTO meals(meal_date,meal_type,meal_name,calories,protein,source,place,rating,note) VALUES(?,?,?,?,?,?,?,?,?)',(date.today().isoformat(),m['type'],m['name'],m['cal'],m['protein'],'Meal Plan','','','')); st.success('Added to today.'); st.rerun()
            st.divider(); st.subheader('Exact grocery amounts from this plan')
            for (item,cat,unit,buy),qty in aggregate_ingredients(plan).items(): st.write(f'• **{item} — {fmt_qty(qty)} {unit} needed** · {buy}')
            if st.button('Refresh Grocery Shopping list from this plan',use_container_width=True): save_plan_grocery(plan); st.success('Grocery list updated.')
        else: st.info('Build a plan to create recipes and the grocery list automatically.')
    with tabs[2]:
        today=date.today().isoformat(); m=df_from('SELECT * FROM meals WHERE meal_date=? ORDER BY id DESC',(today,)); cal=m.calories.sum() if not m.empty else 0; protein=m.protein.sum() if not m.empty else 0
        target=safe_float((get_setting('food_profile',{}) or {}).get('calorie_target',0)); c=st.columns(3); c[0].metric('Calories logged today',f'{cal:.0f}'); c[1].metric('Protein logged',f'{protein:.0f} g'); c[2].metric('Target remaining',f'{max(0,target-cal):.0f}' if target else 'No target')
        if target: st.progress(min(1,cal/target if target else 0))
        if not m.empty: st.dataframe(m[['meal_type','meal_name','calories','protein','source','place']],use_container_width=True,hide_index=True)
        with st.form('meal_log',clear_on_submit=True):
            c=st.columns(4); mt=c[0].selectbox('Meal',['Breakfast','Lunch','Dinner','Snack','Drink','Other']); name=c[1].text_input('Meal / item'); calories=c[2].number_input('Calories',min_value=0.0,step=10.0); protein_g=c[3].number_input('Protein (g)',min_value=0.0,step=1.0)
            note=st.text_input('Notes');
            if st.form_submit_button('Add manually'): execute('INSERT INTO meals(meal_date,meal_type,meal_name,calories,protein,source,place,rating,note) VALUES(?,?,?,?,?,?,?,?,?)',(today,mt,name,calories,protein_g,'Manual','','',note)); st.rerun()
        delete_reset_panel('meals','meal logs','meal_name')
    with tabs[3]:
        st.subheader('Eating Out / Restaurant Tracker')
        place=st.text_input('Restaurant / café / bar / place',placeholder='Chipotle, Starbucks, local restaurant...'); item=st.text_input('Food or drink ordered'); custom=st.text_input('Customizations')
        if place and item:
            q=urllib.parse.quote_plus(f'{place} {item} calories nutrition'); st.link_button('🔎 Search web for nutrition',f'https://www.google.com/search?q={q}',use_container_width=True)
        with st.form('restaurantlog',clear_on_submit=True):
            c=st.columns(3); cal=c[0].number_input('Calories found / estimated',min_value=0.0,step=10.0); prot=c[1].number_input('Protein if known',min_value=0.0,step=1.0); source=c[2].selectbox('Source',['Official nutrition','Restaurant menu','Reliable database','Estimated','Entered myself']); note=st.text_input('Notes')
            if st.form_submit_button('Add to today’s counter',use_container_width=True): execute('INSERT INTO meals(meal_date,meal_type,meal_name,calories,protein,source,place,rating,note) VALUES(?,?,?,?,?,?,?,?,?)',(date.today().isoformat(),'Other',item,cal,prot,source,place,'',f'{custom} {note}'.strip())); st.rerun()

# ---------- Grocery ----------
STORES=['Aldi','ShopRite','Stop & Shop','Target','Walmart','Whole Foods Market','Trader Joe’s','Key Food','Food Bazaar','Costco','BJ’s Wholesale Club','Other']
def grocery():
    st.title('🛒 Grocery Shopping')
    week=date.today()-timedelta(days=date.today().weekday()); prof=get_setting('food_profile',{}) or {}; budget=safe_float(prof.get('budget',0)); store_saved=get_setting('grocery_store','Aldi')
    c=st.columns(2); store=c[0].selectbox('Select grocery store',STORES,index=STORES.index(store_saved) if store_saved in STORES else 0); other=c[1].text_input('Other store name') if store=='Other' else ''
    store_name=other or store
    if store_name and store_name!=store_saved: set_setting('grocery_store',store_name)
    items=df_from('SELECT * FROM grocery_items WHERE week_of=? ORDER BY category,item',(week.isoformat(),)); est=items.estimated_cost.sum() if not items.empty else 0
    c=st.columns(3); c[0].metric('Weekly budget',money(budget)); c[1].metric('Estimated cart',money(est)); c[2].metric('Budget left',money(budget-est))
    if not items.empty:
        st.caption('Needed = exact amount from your meal plan. “Buy” guidance helps avoid buying far more than you need.')
        for _,r in items.iterrows():
            with st.container(border=True):
                c=st.columns([3,2,2]); c[0].markdown(f"**{r['item']}**\n\n{r['category']}"); c[1].markdown(f"Needed: **{r['qty']}**\n\nBuy: {r['note'] or 'closest practical package'}")
                purchased=c[2].checkbox('In cart / purchased',value=bool(r['purchased']),key=f"gchk{r['id']}")
                if purchased!=bool(r['purchased']): execute('UPDATE grocery_items SET purchased=? WHERE id=?',(1 if purchased else 0,int(r['id']))); st.rerun()
                q=urllib.parse.quote_plus(f"{r['item']} {store_name}")
                st.link_button('Search this item on Instacart',f'https://www.instacart.com/store/s?k={q}',use_container_width=True)
        remaining=int((items.purchased==0).sum()); st.info(f'{remaining} item(s) still needed.')
        st.link_button(f'Open Instacart for {store_name}', 'https://www.instacart.com/', use_container_width=True)
    else: st.info('Build a meal plan in Food & Nutrition. Its exact ingredients will appear here automatically.')
    with st.expander('Add extra grocery item'):
        with st.form('groceryadd',clear_on_submit=True):
            c=st.columns(4); item=c[0].text_input('Item'); cat=c[1].selectbox('Category',['Produce','Meat / Protein','Dairy / Eggs','Pantry','Frozen','Snacks','Drinks','Household','Other']); qty=c[2].text_input('Qty'); cost=c[3].number_input('Est. cost',min_value=0.0,step=1.0); note=st.text_input('Buy size / note')
            if st.form_submit_button('Add item'): execute('INSERT INTO grocery_items(week_of,item,category,qty,estimated_cost,purchased,note) VALUES(?,?,?,?,?,?,?)',(week.isoformat(),item,cat,qty,cost,0,note)); st.rerun()
    delete_reset_panel('grocery_items','grocery items','item')

# ---------- Trainer ----------
EXERCISES={'Full Body':['Goblet squat','Dumbbell row','Romanian deadlift','Incline push-up','Shoulder press','Farmer carry'],'Lower Body':['Goblet squat','Romanian deadlift','Reverse lunge','Glute bridge','Calf raise'],'Upper Body':['Dumbbell row','Shoulder press','Chest press','Biceps curl','Triceps extension'],'Core':['Dead bug','Bird dog','Standing knee drive','Suitcase carry','Plank'],'Low Impact Cardio':['Elliptical','Brisk walk','Step touch','March in place']}
def trainer():
    st.title('🏋🏾‍♀️ My Trainer')
    food_goal=(get_setting('food_profile',{}) or {}).get('goal','General health'); st.caption(f'Food plan goal currently connected: **{food_goal}**')
    tabs=st.tabs(['Build Routine','Log Workout','History'])
    with tabs[0]:
        c=st.columns(5); goal=c[0].selectbox('Goal',['Lose weight','Build strength','Tone / definition','Improve stamina','General fitness','Other']); focus=c[1].selectbox('Focus',list(EXERCISES.keys())+['Other']); mins=c[2].selectbox('Time available',[10,15,20,25,30,40,45,60]); level=c[3].selectbox('Difficulty',['Beginner','Easy','Moderate','Challenging']); energy=c[4].selectbox('Energy today',['Low','Okay','Good','High'])
        st.multiselect('Equipment available',['Bodyweight','Dumbbells','Kettlebell','Elliptical','Resistance band','Bench / chair','Other'],default=['Bodyweight']); limitations=st.text_input('Limitations / notes')
        if st.button('Build my routine',use_container_width=True):
            base=EXERCISES.get(focus,EXERCISES['Full Body'])[:]; n=max(3,min(len(base),round(mins/6))); chosen=random.sample(base,n) if len(base)>=n else base; rounds=2 if mins<=20 else 3
            st.session_state.routine={'name':f'{mins}-min {focus}','exercises':chosen,'rounds':rounds,'mins':mins,'focus':focus,'level':level}
        r=st.session_state.get('routine')
        if r:
            st.success(f"{r['name']} • {r['rounds']} rounds")
            for i,e in enumerate(r['exercises'],1): st.write(f'**{i}. {e}** — 8–12 reps or 40 seconds')
            if st.button('✅ Complete & save workout',use_container_width=True): execute('INSERT INTO workouts(workout_date,name,minutes,intensity,focus,completed,note) VALUES(?,?,?,?,?,?,?)',(date.today().isoformat(),r['name'],r['mins'],r['level'],r['focus'],1,limitations)); st.rerun()
    with tabs[1]:
        with st.form('workoutlog',clear_on_submit=True):
            c=st.columns(5); d=c[0].date_input('Date',date.today()); name=c[1].text_input('Workout name'); mins=c[2].number_input('Minutes',0,300,step=5); intensity=c[3].selectbox('Intensity',['Easy','Moderate','Hard']); focus=c[4].selectbox('Focus area',list(EXERCISES.keys())+['Other'],key='lfocus'); note=st.text_input('Notes')
            if st.form_submit_button('Log workout'): execute('INSERT INTO workouts(workout_date,name,minutes,intensity,focus,completed,note) VALUES(?,?,?,?,?,?,?)',(d.isoformat(),name,mins,intensity,focus,1,note)); st.rerun()
    with tabs[2]:
        w=df_from('SELECT * FROM workouts ORDER BY workout_date DESC,id DESC');
        if not w.empty: st.dataframe(w[['workout_date','name','minutes','intensity','focus','note']],use_container_width=True,hide_index=True)
        delete_reset_panel('workouts','workout history','name')

# ---------- Water + random multi-jug game ----------
def neighbors_n(state,caps):
    out=[]; n=len(caps)
    for i in range(n):
        if state[i] < caps[i]:
            s=list(state); s[i]=caps[i]; out.append((tuple(s),f'Fill Jug {chr(65+i)}'))
        if state[i] > 0:
            s=list(state); s[i]=0; out.append((tuple(s),f'Empty Jug {chr(65+i)}'))
        for j in range(n):
            if i==j or state[i]==0 or state[j]>=caps[j]: continue
            p=min(state[i],caps[j]-state[j]); s=list(state); s[i]-=p; s[j]+=p; out.append((tuple(s),f'Pour {chr(65+i)} → {chr(65+j)}'))
    return out

def solve_n(caps,target,max_states=50000):
    start=tuple(0 for _ in caps); q=deque([(start,[])]); seen={start}
    while q and len(seen)<max_states:
        state,path=q.popleft()
        if target in state: return path
        for ns,m in neighbors_n(state,caps):
            if ns not in seen: seen.add(ns); q.append((ns,path+[(m,ns)]))
    return None

JUG_LEVELS={
1:[((5, 2), 4), ((4, 3), 2), ((7, 4), 3)],
2:[((8, 5, 3), 4), ((6, 4, 3), 5), ((9, 5, 2), 7)],
3:[((10, 7, 3), 5), ((9, 4, 3), 6), ((11, 6, 4), 8)],
4:[((12, 7, 5), 9), ((10, 6, 3), 7), ((13, 8, 5), 6)],
5:[((8, 5, 3, 2), 7), ((10, 7, 4, 3), 6), ((9, 6, 4, 2), 5)],
6:[((12, 8, 5, 3), 7), ((11, 7, 5, 2), 9), ((13, 9, 4, 3), 8)],
7:[((14, 9, 5, 3), 11), ((12, 7, 4, 3), 10), ((15, 8, 5, 2), 13)],
8:[((16, 11, 7, 4), 9), ((14, 10, 6, 3), 11), ((15, 9, 5, 4), 12)],
9:[((18, 11, 7, 5), 13), ((17, 10, 6, 4), 15), ((16, 9, 7, 3), 14)],
10:[((20, 13, 8, 5), 17), ((19, 12, 7, 4), 16), ((18, 11, 6, 5), 14)],
11:[((8, 4, 3), 6), ((13, 11, 6), 12), ((13, 9, 2), 10)],
12:[((14, 12, 9), 6), ((11, 3, 2), 8), ((13, 10, 5), 7)],
13:[((13, 7, 4), 11), ((15, 4, 3), 1), ((14, 12, 5), 1)],
14:[((12, 8, 5), 6), ((16, 4, 2), 6), ((16, 10, 4), 8)],
15:[((16, 8, 5), 1), ((11, 8, 6), 2), ((16, 9, 5), 12)],
16:[((17, 16, 3), 6), ((15, 11, 9), 4), ((16, 15, 13), 11)],
17:[((17, 14, 8), 13), ((11, 6, 3), 1), ((8, 5, 2), 4)],
18:[((13, 10, 9), 2), ((14, 6, 2), 10), ((18, 15, 8), 6)],
19:[((18, 11, 3), 5), ((8, 5, 3), 2), ((10, 8, 2), 4)],
20:[((17, 9, 8), 6), ((12, 7, 4), 9), ((7, 5, 2), 3)],
21:[((15, 7, 6), 3), ((17, 7, 6), 8), ((19, 16, 5), 6)],
22:[((17, 7, 2), 6), ((19, 12, 5), 3), ((7, 6, 5), 2)],
23:[((8, 7, 4), 5), ((13, 12, 5), 10), ((16, 8, 6), 14)],
24:[((19, 17, 13), 10), ((19, 18, 15), 13), ((17, 16, 13), 2)],
25:[((17, 10, 9), 5), ((11, 7, 5), 1), ((14, 11, 2), 4)],
26:[((13, 11, 6), 5), ((15, 5, 2), 3), ((19, 18, 7), 8)],
27:[((11, 10, 8), 1), ((17, 10, 5), 9), ((16, 11, 6), 13)],
28:[((19, 17, 9), 12), ((14, 12, 8), 6), ((18, 17, 6), 9)],
29:[((10, 8, 6), 4), ((9, 5, 4), 3), ((21, 18, 2), 19)],
30:[((11, 8, 7), 10), ((21, 10, 3), 18), ((14, 6, 2), 8)],
31:[((18, 16, 11), 14), ((15, 12, 9), 6), ((13, 6, 2), 4)],
32:[((17, 13, 2), 3), ((21, 7, 5), 1), ((21, 20, 19), 14)],
33:[((20, 19, 4), 6), ((20, 17, 10), 6), ((22, 18, 3), 15)],
34:[((20, 11, 10), 16), ((19, 14, 2), 3), ((18, 16, 3), 5)],
35:[((12, 11, 7), 4), ((22, 21, 12), 2), ((18, 12, 10), 16)],
36:[((20, 17, 12, 5), 8), ((25, 20, 9, 2), 23), ((17, 13, 6, 4), 7)],
37:[((20, 16, 12, 11), 2), ((23, 18, 14, 5), 11), ((26, 20, 14, 9), 10)],
38:[((20, 13, 4, 3), 2), ((12, 4, 3, 2), 1), ((24, 18, 17, 12), 4)],
39:[((23, 13, 10, 7), 19), ((27, 26, 25, 6), 1), ((21, 16, 15, 14), 1)],
40:[((24, 21, 8, 7), 5), ((19, 12, 11, 9), 10), ((24, 17, 12, 11), 5)],
41:[((25, 13, 6, 3), 19), ((21, 13, 10, 3), 20), ((25, 21, 17, 15), 10)],
42:[((18, 14, 12, 10), 4), ((20, 13, 11, 5), 6), ((16, 11, 8, 3), 12)],
43:[((22, 21, 19, 9), 3), ((26, 25, 21, 17), 1), ((19, 18, 8, 6), 13)],
44:[((28, 21, 7, 4), 14), ((25, 15, 8, 3), 19), ((26, 9, 3, 2), 7)],
45:[((18, 10, 8, 6), 4), ((28, 20, 18, 16), 22), ((28, 27, 18, 2), 1)],
46:[((22, 19, 18, 5), 15), ((18, 16, 14, 3), 10), ((11, 9, 6, 4), 3)],
47:[((22, 16, 15, 3), 18), ((24, 17, 16, 10), 4), ((27, 10, 3, 2), 8)],
48:[((30, 28, 24, 10), 6), ((18, 17, 15, 13), 3), ((27, 21, 20, 7), 16)],
49:[((23, 21, 9, 8), 18), ((27, 23, 20, 8), 14), ((27, 19, 14, 4), 10)],
50:[((28, 27, 26, 25), 17), ((22, 18, 15, 9), 21), ((23, 11, 10, 4), 18)],
51:[((29, 20, 16, 7), 8), ((29, 19, 18, 11), 15), ((29, 13, 8, 4), 21)],
52:[((24, 21, 13, 6), 7), ((22, 20, 16, 3), 2), ((11, 7, 6, 3), 2)],
53:[((29, 23, 13, 2), 21), ((29, 18, 16, 9), 5), ((21, 19, 17, 6), 16)],
54:[((28, 23, 16, 11), 13), ((23, 16, 7, 4), 10), ((26, 17, 14, 4), 25)],
55:[((25, 20, 10, 6), 7), ((22, 17, 10, 7), 2), ((24, 16, 9, 8), 7)],
56:[((30, 26, 24, 13), 8), ((23, 18, 15, 13), 14), ((26, 17, 11, 3), 20)],
57:[((13, 11, 10, 6), 12), ((24, 22, 10, 5), 20), ((30, 24, 20, 8), 16)],
58:[((19, 15, 9, 3), 17), ((31, 26, 17, 10), 2), ((30, 20, 6, 3), 23)],
59:[((30, 28, 12, 6), 22), ((28, 24, 10, 6), 22), ((18, 16, 13, 6), 11)],
60:[((32, 9, 7, 2), 14), ((32, 29, 26, 6), 12), ((31, 27, 23, 7), 9)],
61:[((30, 22, 15, 2), 11), ((32, 25, 24, 7), 18), ((23, 21, 17, 6), 11)],
62:[((25, 21, 7, 4), 11), ((23, 13, 10, 4), 1), ((25, 20, 16, 7), 10)],
63:[((30, 17, 7, 2), 25), ((24, 18, 11, 10), 23), ((28, 12, 3, 2), 16)],
64:[((23, 11, 9, 4), 16), ((18, 16, 10, 9), 14), ((29, 27, 19, 3), 25)],
65:[((29, 26, 24, 9), 23), ((33, 15, 11, 3), 2), ((30, 19, 14, 6), 7)],
66:[((21, 19, 18, 12), 17), ((33, 17, 15, 9), 21), ((32, 31, 27, 18), 17)],
67:[((28, 14, 6, 5), 1), ((27, 14, 6, 5), 9), ((30, 12, 8, 4), 24)],
68:[((27, 18, 13, 8), 21), ((30, 29, 14, 5), 7), ((23, 20, 7, 5), 2)],
69:[((20, 13, 11, 4), 7), ((25, 18, 14, 10), 12), ((34, 25, 18, 8), 24)],
70:[((35, 26, 18, 11), 10), ((26, 25, 11, 8), 4), ((29, 28, 4, 2), 23)],
71:[((29, 28, 18, 10), 13), ((24, 23, 18, 13), 2), ((31, 23, 17, 2), 19)],
72:[((36, 33, 21, 18), 27), ((30, 29, 27, 9), 16), ((29, 10, 8, 6), 21)],
73:[((34, 32, 22, 10), 8), ((27, 21, 19, 12), 22), ((33, 32, 18, 15), 17)],
74:[((31, 26, 23, 16), 1), ((36, 16, 15, 6), 30), ((30, 23, 20, 10), 14)],
75:[((31, 24, 23, 2), 30), ((25, 20, 14, 8), 12), ((29, 24, 6, 4), 2)],
76:[((36, 27, 11, 7), 5), ((37, 17, 15, 6), 31), ((30, 28, 17, 8), 19)],
77:[((28, 26, 13, 11), 20), ((31, 17, 7, 2), 29), ((35, 25, 14, 6), 4)],
78:[((32, 31, 17, 8), 30), ((15, 10, 8, 3), 7), ((31, 28, 13, 4), 12)],
79:[((31, 24, 12, 4), 3), ((23, 21, 19, 8), 17), ((32, 27, 13, 2), 5)],
80:[((24, 23, 16, 9), 14), ((36, 27, 24, 11), 10), ((36, 14, 11, 7), 28)],
81:[((45, 22, 10, 5), 16), ((37, 26, 18, 10), 36), ((36, 30, 28, 6), 16)],
82:[((40, 19, 14, 5), 27), ((47, 25, 17, 8), 15), ((42, 40, 27, 15), 37)],
83:[((35, 19, 17, 11), 33), ((36, 29, 18, 9), 35), ((45, 42, 5, 3), 14)],
84:[((30, 25, 24, 4), 14), ((49, 46, 40, 25), 34), ((49, 39, 29, 22), 44)],
85:[((29, 28, 26, 15), 17), ((37, 32, 23, 15), 36), ((43, 38, 23, 20), 16)],
86:[((49, 43, 33, 12), 10), ((35, 34, 22, 13), 4), ((45, 31, 29, 17), 39)],
87:[((48, 19, 13, 4), 25), ((24, 23, 16, 10), 11), ((48, 29, 6, 5), 39)],
88:[((45, 36, 19, 9), 4), ((37, 27, 16, 14), 32), ((45, 24, 12, 11), 39)],
89:[((49, 36, 16, 2), 46), ((50, 21, 10, 5), 15), ((28, 26, 8, 7), 10)],
90:[((44, 14, 5, 2), 17), ((44, 27, 24, 16), 19), ((44, 38, 22, 11), 17)],
91:[((45, 44, 21, 3), 41), ((33, 28, 12, 3), 6), ((41, 16, 4, 2), 21)],
92:[((46, 45, 33, 27), 4), ((46, 21, 16, 12), 8), ((32, 24, 12, 2), 16)],
93:[((23, 19, 17, 12), 9), ((47, 20, 16, 10), 30), ((44, 43, 18, 16), 28)],
94:[((44, 39, 21, 9), 25), ((48, 44, 25, 4), 2), ((17, 16, 8, 2), 12)],
95:[((45, 37, 22, 14), 21), ((33, 31, 19, 9), 8), ((21, 13, 7, 3), 1)],
96:[((43, 34, 24, 19), 6), ((46, 43, 15, 5), 19), ((52, 38, 13, 5), 22)],
97:[((48, 47, 45, 23), 44), ((50, 43, 19, 10), 39), ((44, 30, 9, 4), 22)],
98:[((51, 30, 18, 6), 15), ((50, 26, 14, 3), 32), ((48, 43, 22, 13), 21)],
99:[((38, 36, 24, 3), 18), ((49, 38, 18, 16), 44), ((48, 27, 14, 9), 46)],
100:[((49, 24, 13, 4), 33), ((41, 38, 29, 5), 23), ((43, 36, 17, 13), 33)],
101:[((48, 46, 33, 31), 20), ((31, 28, 24, 6), 29), ((33, 31, 30, 25), 32)],
102:[((53, 37, 36, 9), 41), ((50, 45, 25, 21), 28), ((46, 34, 21, 12), 40)],
103:[((53, 21, 17, 12), 8), ((22, 16, 10, 7), 2), ((49, 41, 38, 13), 8)],
104:[((50, 31, 4, 3), 9), ((44, 38, 24, 8), 10), ((34, 32, 17, 4), 19)],
105:[((37, 14, 10, 2), 31), ((52, 40, 38, 18), 16), ((39, 34, 11, 8), 27)],
106:[((38, 25, 13, 2), 32), ((49, 32, 8, 4), 30), ((47, 38, 22, 7), 28)],
107:[((52, 29, 14, 10), 7), ((40, 38, 37, 13), 5), ((50, 17, 8, 5), 33)],
108:[((53, 40, 33, 17), 4), ((55, 44, 35, 29), 27), ((42, 20, 17, 2), 9)],
109:[((53, 43, 26, 17), 23), ((37, 30, 25, 24), 35), ((49, 48, 7, 2), 35)],
110:[((50, 32, 22, 8), 12), ((45, 39, 35, 5), 4), ((54, 37, 24, 20), 42)],
111:[((48, 32, 31, 6), 34), ((49, 45, 43, 17), 10), ((54, 46, 45, 38), 52)],
112:[((48, 38, 28, 14), 32), ((49, 23, 17, 2), 13), ((45, 34, 28, 24), 10)],
113:[((41, 35, 31, 28), 27), ((52, 34, 30, 9), 40), ((54, 45, 23, 9), 52)],
114:[((44, 15, 9, 8), 33), ((45, 23, 16, 2), 44), ((50, 35, 33, 32), 10)],
115:[((42, 38, 32, 12), 4), ((37, 31, 30, 21), 26), ((37, 28, 26, 24), 2)],
116:[((55, 42, 37, 36), 38), ((51, 29, 20, 11), 9), ((35, 22, 13, 3), 28)],
117:[((53, 49, 44, 24), 9), ((49, 43, 41, 12), 47), ((27, 13, 12, 6), 19)],
118:[((55, 46, 29, 21), 54), ((54, 44, 32, 3), 34), ((50, 45, 43, 29), 33)],
119:[((34, 16, 10, 2), 28), ((54, 24, 20, 15), 35), ((54, 47, 44, 28), 30)],
120:[((42, 40, 39, 20), 41), ((53, 50, 41, 3), 33), ((56, 45, 38, 16), 41)],
}

def new_jug_puzzle(level):
    candidates=JUG_LEVELS[level][:]; random.shuffle(candidates)
    for caps,target in candidates:
        sol=solve_n(caps,target)
        if sol: return {'caps':caps,'target':target,'solution':sol}
    caps,target=candidates[0]; return {'caps':caps,'target':target,'solution':solve_n(caps,target) or []}

def water_page():
    st.title('💧 Water & Jug Puzzles')
    tabs=st.tabs(['Water Tracker','Jug Puzzle'])
    with tabs[0]:
        goal=safe_float(get_setting('water_goal',64)); ng=st.number_input('Daily water goal (oz)',8.0,256.0,step=8.0,value=goal)
        if ng!=goal: set_setting('water_goal',ng)
        today=date.today().isoformat(); total=sum(r['ounces'] for r in rows('SELECT ounces FROM water_log WHERE log_date=?',(today,))); st.metric('Today',f'{total:.0f} oz',f'{max(0,ng-total):.0f} oz remaining'); st.progress(min(1,total/ng if ng else 0))
        c=st.columns(5)
        for i,oz in enumerate([8,12,16,20,24]):
            if c[i].button(f'+ {oz} oz',use_container_width=True): execute('INSERT INTO water_log(log_date,ounces) VALUES(?,?)',(today,oz)); st.rerun()
        if st.button('Undo last water entry'):
            r=rows('SELECT id FROM water_log WHERE log_date=? ORDER BY id DESC LIMIT 1',(today,));
            if r: delete_row('water_log',r[0]['id']); st.rerun()
        delete_reset_panel('water_log','water history')
    with tabs[1]:
        unlocked=int(get_setting('jug_unlocked',1) or 1); passed=set(get_setting('jug_passed',[]) or [])
        st.caption('Pass a level to unlock the next. Passed levels stay available to replay. Puzzles are generated for you — no setup required.')
        level=st.selectbox('Level',list(range(1,unlocked+1)),index=min(unlocked-1,max(0,int(st.session_state.get('jug_level',1))-1)))
        if st.session_state.get('jug_level')!=level or 'jug_puzzle' not in st.session_state:
            st.session_state.jug_level=level
            st.session_state.jug_puzzle=new_jug_puzzle(level)
            st.session_state.jug_state=tuple(0 for _ in st.session_state.jug_puzzle['caps'])
            st.session_state.jug_selected=None
            st.session_state.jug_moves=[]
            st.session_state.jug_started=False
        p=st.session_state.jug_puzzle; caps=p['caps']; state=st.session_state.jug_state; target=p['target']; selected=st.session_state.jug_selected
        st.subheader(f'Level {level} — Make exactly {target} gallons in any jug')
        if level<=10: tier='Starter'
        elif level<=35: tier='Skilled'
        elif level<=80: tier='Advanced'
        else: tier='Expert'
        st.caption(f'🏆 {tier} challenge • Level {level} of {max(JUG_LEVELS)}')
        started=bool(st.session_state.get('jug_started',False))
        if not started:
            st.info('Press **Start Level** when you are ready. Then tap directly on a jug to select it.')
            if st.button('▶ Start Level',key=f'jugstart_{level}',use_container_width=True,type='primary'):
                st.session_state.jug_started=True
                st.session_state.jug_selected=None
                st.session_state.jug_state=tuple(0 for _ in caps)
                st.session_state.jug_moves=[]
                st.rerun()
            started=False
        else:
            st.success('Level started — tap a jug to select it.')
        if level in passed: st.success('✓ Passed before — replay anytime.')
        # Preserve the original v2.1 jug artwork and water layer; the Streamlit button itself sits invisibly over the picture.
        st.markdown("""<style>
        /* Robust clickable overlay: Streamlit exposes each keyed widget with a st-key-* class. */
        [class*="st-key-jugsel_"] {
            margin-top: -238px !important;
            height: 218px !important;
            position: relative !important;
            z-index: 40 !important;
        }
        [class*="st-key-jugsel_"] button {
            height: 210px !important;
            width: 100% !important;
            max-width: 165px !important;
            margin: 0 auto !important;
            display: block !important;
            background: rgba(255,255,255,0.001) !important;
            border: 0 !important;
            box-shadow: none !important;
            cursor: pointer !important;
        }
        [class*="st-key-jugsel_"] button p { opacity: 0 !important; }
        [class*="st-key-jugsel_"] button:focus-visible {
            outline: 3px solid #4f8cff !important;
            outline-offset: 2px !important;
            border-radius: 20px !important;
        }
        @media(max-width:640px){
            [class*="st-key-jugsel_"] { margin-top:-195px !important; height:178px !important; }
            [class*="st-key-jugsel_"] button { height:170px !important; max-width:125px !important; }
        }
        </style>""", unsafe_allow_html=True)
        cols=st.columns(len(caps))
        for i,cap in enumerate(caps):
            with cols[i]:
                cls='jugwrap selected' if selected==i else 'jugwrap'; pct=(state[i]/cap)*100 if cap else 0
                st.markdown(f'<div class="{cls}"><div class="jug"><div class="water" style="height:{pct}%"></div></div><div class="juglabel">Jug {chr(65+i)}: {state[i]} / {cap} gal</div></div>',unsafe_allow_html=True)
                if st.button(f'Jug {chr(65+i)}',key=f'jugsel_{level}_{i}',use_container_width=True,type='tertiary',disabled=not started):
                    if selected is None:
                        st.session_state.jug_selected=i
                    elif selected==i:
                        st.session_state.jug_selected=None
                    else:
                        src=selected; dst=i; s=list(state); amount=min(s[src],caps[dst]-s[dst]); s[src]-=amount; s[dst]+=amount
                        st.session_state.jug_state=tuple(s); st.session_state.jug_moves.append(f'Pour {chr(65+src)} → {chr(65+dst)}'); st.session_state.jug_selected=dst
                    st.rerun()
        st.caption('Tap directly on a jug to select it. The selected jug glows. Water fills inside the jug; tapping another jug pours into it and selects the receiving jug. Tap the selected jug again to clear the glow.')
        c=st.columns(3)
        if c[0].button('💧 Water',use_container_width=True,disabled=(not started or selected is None)):
            s=list(state); s[selected]=caps[selected]; st.session_state.jug_state=tuple(s); st.session_state.jug_moves.append(f'Fill {chr(65+selected)}'); st.rerun()
        if c[1].button('🪣 Empty',use_container_width=True,disabled=(not started or selected is None)):
            s=list(state); s[selected]=0; st.session_state.jug_state=tuple(s); st.session_state.jug_moves.append(f'Empty {chr(65+selected)}'); st.rerun()
        if c[2].button('↩ Reset Level',use_container_width=True,disabled=not started):
            st.session_state.jug_state=tuple(0 for _ in caps)
            st.session_state.jug_selected=None
            st.session_state.jug_moves=[]
            st.rerun()
        if started and target in st.session_state.jug_state:
            if level not in passed:
                passed.add(level); set_setting('jug_passed',sorted(passed));
                if level==unlocked and level<max(JUG_LEVELS): set_setting('jug_unlocked',level+1)
            st.success(f'🎉 Level {level} passed! {"Level "+str(level+1)+" is now unlocked." if level==unlocked and level<max(JUG_LEVELS) else ""}')
            if level < max(JUG_LEVELS):
                if st.button(f'Next Level → {level+1}',key=f'jugnext_{level}',use_container_width=True,type='primary'):
                    st.session_state.jug_level=level+1
                    st.session_state.jug_puzzle=new_jug_puzzle(level+1)
                    st.session_state.jug_state=tuple(0 for _ in st.session_state.jug_puzzle['caps'])
                    st.session_state.jug_selected=None
                    st.session_state.jug_moves=[]
                    st.session_state.jug_started=False
                    st.rerun()
            else:
                st.success('🏆 You completed the highest jug level!')
        with st.expander('Need help?'):
            if st.button('Hint',key='jughint'):
                current=st.session_state.jug_state; sol=None
                q=deque([(current,[])]); seen={current}
                while q:
                    state0,path=q.popleft()
                    if target in state0: sol=path; break
                    for ns,m in neighbors_n(state0,caps):
                        if ns not in seen: seen.add(ns); q.append((ns,path+[(m,ns)]))
                if sol: st.info(f'Next move: {sol[0][0]}')
            if st.button('Show full solution',key='jugsol'):
                for n,(m,s) in enumerate(p['solution'],1): st.write(f'{n}. {m} → {s}')

# ---------- Vocabulary ----------
WORDS=[
('Pragmatic','adjective','dealing with problems in a practical, realistic way','She took a pragmatic approach and chose the option that worked best.','Think: practical = pragmatic.'),
('Astute','adjective','able to understand a situation quickly and accurately','Her astute observation helped the team catch the mistake early.','Picture an owl noticing a tiny detail.'),
('Concise','adjective','giving a lot of information clearly and in few words','His project update was concise but complete.','Concise = cut the extra words.'),
('Meticulous','adjective','very careful and precise about details','She kept meticulous records of every change order.','Imagine checking a list twice, line by line.'),
('Proactive','adjective','taking action before a problem happens','A proactive coordinator follows up before a deadline is missed.','Pro = before trouble; active = doing something.'),
('Viable','adjective','capable of working successfully','The team needed a viable solution that fit the budget.','Viable = it can actually work.'),
('Diligent','adjective','showing steady, careful effort','Her diligent follow-up kept the submittal log current.','Diligent = doing the work consistently.'),
('Articulate','adjective','able to express ideas clearly','He gave an articulate explanation during the meeting.','Articulate = clear words, clear thought.'),
('Resilient','adjective','able to recover and keep going after difficulty','She stayed resilient after a challenging week.','Think of a spring bouncing back.'),
('Discern','verb','to recognize or understand something clearly','She could discern which issue required immediate attention.','Discern = detect the difference.')]

SENTENCE_CONTEXT={
    'Pragmatic':['practical','realistic','solution','approach','choice','workable','problem','plan','decision','budget'],
    'Astute':['notice','noticed','observation','insight','recognize','recognized','detail','judgment','aware','detect','caught','understand'],
    'Concise':['brief','short','clear','summary','update','explanation','few words','straight','direct','complete'],
    'Meticulous':['careful','detail','precise','record','check','organized','thorough','exact','review','double-check'],
    'Proactive':['before','ahead','early','prevent','prepare','follow up','follow-up','anticipated','deadline','in advance'],
    'Viable':['solution','option','plan','workable','feasible','successful','budget','alternative','possible','choice'],
    'Diligent':['steady','consistently','careful','effort','follow-up','follow up','completed','maintained','regularly','thorough'],
    'Articulate':['explain','clearly','expressed','presentation','communicate','idea','speech','described','words','thought'],
    'Resilient':['recover','bounced','continued','setback','difficulty','challenge','keep going','kept going','adapted','after'],
    'Discern':['distinguish','recognize','difference','determine','identify','understand','see','tell','which','between']
}

def sentence_feedback(word, sentence):
    text=' '.join(sentence.strip().lower().split())
    target=word.lower()
    cleaned=text
    for ch in ',.!?;:"“”()':
        cleaned=cleaned.replace(ch,' ')
    tokens=cleaned.split()
    if not text:
        return False, 'Write a complete sentence first.'
    if target not in tokens:
        return False, f'Use the actual word “{word}” in your sentence so I can check it.'
    if len(tokens) < 5:
        return False, 'Add a little more context so the meaning of the word is clear.'
    clues=SENTENCE_CONTEXT.get(word,[])
    if any(c in text for c in clues):
        return True, f'Yes — that looks like a correct use of “{word}.” Your sentence gives enough context to show the meaning.'
    definition=next(x[2] for x in WORDS if x[0]==word)
    return False, f'I would revise this one. “{word}” means {definition}. Add context that shows that meaning more clearly.'

def speak_widget(word):
    safe=word.replace("'","\\'")
    html = f'''<button id="speak" style="width:100%;min-height:46px;border-radius:12px;border:1px solid #999;background:transparent;font-weight:700;cursor:pointer">🔊 Hear “{word}”</button><script>document.getElementById('speak').onclick=()=>{{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance('{safe}');u.rate=.82;speechSynthesis.speak(u);}};</script>'''
    components.html(html,height=58)

def _quiz_state_for(word, definition):
    key=f'vocab_quiz_options_{word}'
    if key not in st.session_state:
        wrong=[x[2] for x in WORDS if x[0]!=word]
        opts=[definition]+random.sample(wrong,3)
        random.shuffle(opts)
        st.session_state[key]=opts
    return st.session_state[key]

def vocabulary():
    st.title('📖 Vocabulary')
    base=(date.today()-date(2026,1,1)).days % len(WORDS)
    idx=st.session_state.get('vocab_idx',base)
    w,pos,definition,ex,memory=WORDS[idx%len(WORDS)]

    activity_key='vocab_activity'
    current_activity=st.session_state.get(activity_key,'Use it in your own sentence')
    answer_key=f'defquiz_{w}'
    submitted_key=f'defquiz_submitted_{w}'
    selected_answer=st.session_state.get(answer_key)
    submitted=st.session_state.get(submitted_key,False)
    hide_word=(current_activity=='Definition check' and selected_answer is not None and not submitted)

    display_word='••••••' if hide_word else w
    display_definition='Choose your answer below — the word will return after you submit.' if hide_word else f'<b>{pos}</b> — {definition}'
    display_example='' if hide_word else f'<p><i>Example:</i> {ex}</p>'
    st.markdown(f'<div class="hero"><h1>{display_word}</h1><p>{display_definition}</p>{display_example}</div>',unsafe_allow_html=True)
    if hide_word:
        st.caption('🙈 The word is hidden while you decide. Submit your answer to reveal it again.')
    else:
        speak_widget(w)
        st.info(f'🧠 Memory hook: **{memory}**')

    st.subheader('Make it stick')
    activity=st.radio('Choose a quick memory activity',['Use it in your own sentence','Definition check','Recall it later'],horizontal=True,key=activity_key)

    if activity=='Use it in your own sentence':
        sentence=st.text_input(f'Write one sentence using “{w}”',key=f'sentence_{w}')
        c=st.columns(2)
        if c[0].button('Check my sentence',use_container_width=True,key=f'check_sentence_{w}'):
            st.session_state[f'sentence_result_{w}']=sentence_feedback(w,sentence)
        if c[1].button('Clear sentence',use_container_width=True,key=f'clear_sentence_{w}'):
            st.session_state[f'sentence_{w}']=''
            st.session_state.pop(f'sentence_result_{w}',None)
            st.rerun()
        result=st.session_state.get(f'sentence_result_{w}')
        if result:
            ok,msg=result
            if ok:
                st.success('✅ '+msg)
                if st.button('Save this correct sentence',use_container_width=True,key=f'save_sentence_{w}'):
                    execute('INSERT INTO vocab_progress(word,status,saved_date,note) VALUES(?,?,?,?)',(w,'Correct practice sentence',date.today().isoformat(),sentence))
                    st.success('Saved to your vocabulary progress.')
            else:
                st.warning('✏️ '+msg)
                st.caption(f'Example to compare: {ex}')

    elif activity=='Definition check':
        opts=_quiz_state_for(w,definition)
        answer=st.radio('Which definition matches the hidden word?',opts,index=None,key=answer_key)
        if answer is not None and not st.session_state.get(submitted_key,False):
            st.caption('The word above is now hidden. Lock in your choice when you are ready.')
        if st.button('Submit answer',use_container_width=True,key=f'check_def_{w}',disabled=answer is None):
            st.session_state[submitted_key]=True
            st.rerun()
        if st.session_state.get(submitted_key,False):
            chosen=st.session_state.get(answer_key)
            if chosen==definition:
                st.success(f'✅ Correct! The word was **{w}**.')
            else:
                st.error(f'Not quite. The word was **{w}**.')
                st.info(f'Correct definition: {definition}')
            if st.button('Try this word again with mixed choices',use_container_width=True,key=f'retry_def_{w}'):
                wrong=[x[2] for x in WORDS if x[0]!=w]
                opts=[definition]+random.sample(wrong,3)
                random.shuffle(opts)
                st.session_state[f'vocab_quiz_options_{w}']=opts
                st.session_state[submitted_key]=False
                st.session_state[answer_key]=None
                st.rerun()

    else:
        st.write('Look away from the definition for a moment. Then type what you remember in your own words.')
        recall=st.text_area('What does it mean?',key=f'recall_{w}')
        if recall and st.button('Reveal & save recall',use_container_width=True,key=f'reveal_recall_{w}'):
            st.info(definition)
            execute('INSERT INTO vocab_progress(word,status,saved_date,note) VALUES(?,?,?,?)',(w,'Recall practice',date.today().isoformat(),recall))

    c=st.columns(3)
    if c[0].button('❤️ Save word',use_container_width=True):
        execute('INSERT INTO vocab_progress(word,status,saved_date,note) VALUES(?,?,?,?)',(w,'Saved',date.today().isoformat(),'')); st.rerun()
    if c[1].button('✅ I learned this',use_container_width=True):
        execute('INSERT INTO vocab_progress(word,status,saved_date,note) VALUES(?,?,?,?)',(w,'Learned',date.today().isoformat(),'')); st.rerun()
    if c[2].button('🎲 Another word',use_container_width=True):
        old_word=w
        st.session_state.vocab_idx=random.choice([i for i in range(len(WORDS)) if i != idx%len(WORDS)])
        st.session_state.pop(f'defquiz_{old_word}',None)
        st.session_state.pop(f'defquiz_submitted_{old_word}',None)
        st.rerun()

    vp=df_from('SELECT * FROM vocab_progress ORDER BY id DESC')
    if not vp.empty:
        st.dataframe(vp[['word','status','saved_date','note']].head(20),use_container_width=True,hide_index=True)
    delete_reset_panel('vocab_progress','vocabulary progress','word')

# ---------- Growth Lab ----------
GROWTH_COACH={
'Career Confidence':{
'advice':['Confidence grows from evidence. Pick one skill today and practice it instead of waiting to feel ready.','When you feel unsure at work, separate what you know, what you need to verify, and what your next action is.','A clear status update is a confidence skill: completed, pending, next step.'],
'exercises':['Write 3 things you handled well recently and name the skill each required.','Give a 60-second update: what happened, what you did, what happens next.','Choose one work decision and explain your reasoning in 3 direct sentences.'],
'practice':['Your manager asks for an update and you are not completely finished. Give a calm status update without over-apologizing.','A coworker questions your decision. Explain your reasoning clearly without becoming defensive.','You notice a problem before your manager does. Practice how you would raise it and propose a next step.'],
'examples':['“I completed the vendor follow-up and updated the tracker. I am waiting on one response and will follow up again by 2 PM.”','“I noticed a conflict, documented it, and brought it to the PM before work continued.”']},
'Interview Confidence':{
'advice':['Build a bank of true stories instead of memorizing perfect speeches. Structure sounds more confident than performance.','Answer the question first, then give the example. Long introductions can hide your strongest point.','Specific actions make interview answers believable: say what YOU coordinated, tracked, solved, or changed.'],
'exercises':['Answer “Tell me about yourself” in 45–60 seconds.','Build one STAR story from a real problem you solved.','Write 5 strong action verbs that describe work you have actually done.'],
'practice':['Tell me about a time you had several priorities due at once.','Tell me about a difficult stakeholder and how you handled the relationship.','Why are you moving into project coordination, and what experience transfers?'],
'examples':['Weak: “I am good at multitasking.”','Stronger: “I tracked competing deadlines, prioritized items affecting others first, and used a daily checklist so nothing missed its due date.”']},
'Boundaries':{
'advice':['A boundary can be warm and still be definite. You do not need a courtroom argument to justify a no.','Over-explaining can accidentally make a boundary sound negotiable. State the limit, then stop.','An alternative is optional. Offer one when you genuinely want to—not because you feel guilty.'],
'exercises':['Rewrite one over-explained “no” into one or two sentences.','Practice offering one alternative without changing your boundary.','Name one situation where you agree before checking your own capacity.'],
'practice':['Someone asks you to take on something you do not have capacity for. Decline without inventing an excuse.','Someone keeps pushing after you already said no. Respond a second time without adding a new explanation.','A friend changes plans at the last minute in a way that inconveniences you. State what you can do.'],
'examples':['“I can’t take that on today, but I can look at it Thursday.”','“That doesn’t work for me.”']},
'Social Confidence':{
'advice':['You do not need a perfect line. Notice something, add a thought, then ask a question.','Good conversation is shared—not an interview. Ask, react, and add something about yourself too.','When you do not know a topic, curiosity is participation. You can ask for the missing context without pretending.'],
'exercises':['Write an observation + thought + question you could use at a social event.','Turn “that’s crazy” into a reaction + your thought + a follow-up question.','Practice ending a conversation naturally in one sentence.'],
'practice':['You are at an event and know only one person. Introduce yourself to someone nearby.','A coworker tells you about a show you have never watched. Keep the conversation going without pretending you saw it.','You enter a group where three people are already talking. Practice how you would join in.'],
'examples':['“I keep hearing about that show but haven’t watched it yet. What makes everybody so hooked?”','“That outcome surprised me because I thought they were going the other way. What did you think?”']},
'Self-Trust & Decisions':{
'advice':['Self-trust is making a reasonable choice with the information you have and knowing you can adjust later.','Not every decision deserves more research. Decide what information would actually change your choice.','A decision can be good enough without being guaranteed perfect.'],
'exercises':['Make one low-risk decision with a 5-minute limit.','List what information you need versus what would only reassure you.','Write one decision you handled successfully—even if you had to adjust later.'],
'practice':['You have two reasonable choices and keep reopening the decision. Choose using 3 criteria and explain why it is good enough.','You made a choice and someone disagrees. Practice hearing them without automatically abandoning your decision.','You have incomplete information but must decide today. State your assumptions and make the call.'],
'examples':['“Option A fits my budget and schedule better, so I’m choosing A and moving on.”']},
'Communication':{
'advice':['Strong communication makes the point easy to find: situation, need, next step.','Before sending a long message, ask: what do I actually need this person to know or do?','A direct clarifying question is often better than guessing and fixing a mistake later.'],
'exercises':['Turn a long message into 3 sentences: situation, need, next step.','Write one direct clarifying question for an unclear request.','Rewrite a message after removing every repeated point.'],
'practice':['A coworker has not sent something you need. Write a polite, direct follow-up with a deadline.','Someone misunderstood your message. Clarify it without blaming them.','You need to disagree in a meeting while keeping the conversation productive.'],
'examples':['“Following up on the revised quote. I need it by 3 PM to complete today’s package. Can you confirm you’ll have it over by then?”']}
}

def evaluate_growth(text, area):
    t=(text or '').strip(); words=t.split(); score=0; notes=[]
    if len(words)>=12: score+=2
    else: notes.append('Add a little more detail so your response shows what you would actually say or do.')
    if any(x in t.lower() for x in ['because','so that','next','will','can','need','plan']): score+=2
    else: notes.append('Make the next step or your reasoning more explicit.')
    if area in ['Social Confidence','Communication'] and '?' in t: score+=2
    elif area in ['Social Confidence','Communication']: notes.append('Try adding a natural follow-up question when the situation calls for one.')
    if area=='Boundaries' and len(words)<=55: score+=2
    elif area=='Boundaries': notes.append('Try making the boundary shorter and more definite.')
    if not any(x in t.lower() for x in ['sorry but','i guess','maybe i can','that’s crazy','thats crazy']): score+=2
    else: notes.append('Try replacing soft/repeated filler with a specific reaction, limit, or opinion.')
    score=min(10,score+2)
    level='Applied / Independent' if score>=9 else 'Challenge' if score>=7 else 'Guided Practice' if score>=5 else 'Learning'
    return score,level,notes or ['Strong response. Your next activity will raise the difficulty.']

def growth():
    st.title('🌱 Growth Lab')
    st.caption('Fresh daily advice • submit an exercise or practice • get feedback • receive the next activity based on how you did.')
    area=st.selectbox('What do you want help with?',list(GROWTH_COACH)+['Other / write in'])
    if area=='Other / write in':
        chosen=st.text_input('What do you want help with?'); st.info('Custom areas can be journaled here.'); coach=None
    else: chosen=area; coach=GROWTH_COACH[area]
    if coach:
        day_idx=(date.today().toordinal()+sum(map(ord,area)))%len(coach['advice'])
        history=rows('SELECT * FROM growth_log WHERE area=? ORDER BY id DESC',(area,))
        completed=len(history); ex_idx=completed%len(coach['exercises']); pr_idx=completed%len(coach['practice'])
        tabs=st.tabs(['💡 Today’s Advice','🧠 Exercise','🎭 Practice','👀 Examples','📈 My Progress'])
        with tabs[0]:
            st.subheader('Today’s advice'); st.info(coach['advice'][day_idx]); st.caption('A new advice card appears each day. Previous work stays in My Progress.')
        with tabs[1]:
            task=coach['exercises'][ex_idx]; st.subheader('Your exercise'); st.write(task)
            ans=st.text_area('Complete the exercise',key=f'gex_{area}_{completed}')
            if st.button('Complete & evaluate exercise',use_container_width=True):
                if not ans.strip(): st.warning('Write your response first.')
                else:
                    score,level,notes=evaluate_growth(ans,area); execute('INSERT INTO growth_log(log_date,area,activity,rating,note) VALUES(?,?,?,?,?)',(date.today().isoformat(),area,'Exercise: '+task,score,ans))
                    st.success(f'Completed • {score}/10 • {level}'); [st.write('• '+n) for n in notes]; st.info('Your next exercise will change based on this completion.'); st.rerun()
        with tabs[2]:
            task=coach['practice'][pr_idx]; st.subheader('Practice situation'); st.write(task)
            ans=st.text_area('What would you say or do?',key=f'gpr_{area}_{completed}')
            if st.button('Submit practice for feedback',use_container_width=True):
                if not ans.strip(): st.warning('Give the situation a try first.')
                else:
                    score,level,notes=evaluate_growth(ans,area); execute('INSERT INTO growth_log(log_date,area,activity,rating,note) VALUES(?,?,?,?,?)',(date.today().isoformat(),area,'Practice: '+task,score,ans))
                    st.success(f'{score}/10 • {level}'); [st.write('• '+n) for n in notes]; st.info('The next practice will adapt to your progress.'); st.rerun()
        with tabs[3]:
            for x in coach['examples']: st.success(x)
        with tabs[4]:
            g=df_from('SELECT * FROM growth_log WHERE area=? ORDER BY id DESC',(area,))
            if not g.empty: st.metric('Completed activities',len(g)); st.dataframe(g,use_container_width=True,hide_index=True)
            else: st.info('Complete an exercise or practice to begin your progress history.')
            delete_reset_panel('growth_log','growth entries','area')
    else:
        note=st.text_area('Practice / notes'); rating=st.slider('How confident do you feel?',1,10,5)
        if st.button('Save to Growth Lab',use_container_width=True) and (chosen or note): execute('INSERT INTO growth_log(log_date,area,activity,rating,note) VALUES(?,?,?,?,?)',(date.today().isoformat(),chosen or 'Other','Custom practice',rating,note)); st.rerun()

# ---------- Conversation & Current Events ----------
NEWS_QUERIES={'🏛️ Politics':'US politics','🎤 Hip-Hop & Music':'hip hop music','📺 Reality TV':'reality television','🎬 Entertainment':'entertainment celebrities','🏈 Sports':'sports','🌎 Big News':'top news','💻 Tech & Internet':'technology internet','💵 Money & Economy':'economy money','🔥 What People Are Talking About':'trending culture'}

def fetch_news(query, limit=8):
    try:
        url='https://news.google.com/rss/search?q='+urllib.parse.quote(query)+'&hl=en-US&gl=US&ceid=US:en'
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}); raw=urllib.request.urlopen(req,timeout=5).read(); root=ET.fromstring(raw)
        out=[]
        for it in root.findall('.//item')[:limit]:
            title=html.unescape(it.findtext('title') or ''); link=it.findtext('link') or ''; pub=it.findtext('pubDate') or ''
            source=it.find('source').text if it.find('source') is not None else ''
            out.append({'title':title,'link':link,'source':source,'pub':pub})
        return out
    except Exception: return []

def conversation_feedback(text):
    low=text.lower(); tips=[]; score=5
    if '?' in text: score+=1
    else: tips.append('Add a follow-up question so the other person has an easy way to continue.')
    if len(text.split())>=10: score+=1
    else: tips.append('Add one thought, detail, or opinion of your own.')
    fillers=sum(low.count(x) for x in ["that's crazy","thats crazy","i can't believe it","i cant believe it","wow"])
    if fillers: tips.append('You used a familiar reaction phrase. Keep the reaction, then add WHY it surprised you or what you think about it.')
    else: score+=1
    if any(x in low for x in ['i think','to me','what surprised','i heard','i saw','i wonder','because']): score+=1
    else: tips.append('Try contributing a small opinion or observation before your next question.')
    return min(10,score),tips or ['Nice balance: you reacted, contributed something, and kept the conversation open.']

def current_events():
    st.title('💬 Conversation & Current Events')
    st.caption('Catch up simply, recognize the people, then practice talking about what you just read.')
    tabs=st.tabs(['🗞️ Catch Me Up','👤 People to Know','💬 Practice Conversation','📈 Conversation Progress'])
    with tabs[0]:
        cat=st.selectbox('What do you want to catch up on?',list(NEWS_QUERIES))
        if st.button('Refresh current stories',use_container_width=True) or 'news_items' not in st.session_state or st.session_state.get('news_cat')!=cat:
            st.session_state.news_items=fetch_news(NEWS_QUERIES[cat]); st.session_state.news_cat=cat
        items=st.session_state.get('news_items',[])
        if not items: st.warning('I could not reach live news right now. Check your internet connection and press Refresh.')
        for i,item in enumerate(items):
            with st.expander(item['title']):
                st.caption(f"{item['source']} • {item['pub'][:16]}")
                st.write('**What happened:** This is the current headline. Open the source for the full reporting, then use Conversation Practice to work with the topic.')
                st.write('**Conversation angle:** What surprised you? Why do you think people care? What would you want clarified before forming an opinion?')
                st.markdown(f"[Read full story]({item['link']})")
                if st.button('Practice this story',key=f'pracstory_{i}'):
                    st.session_state.practice_story=item['title']; st.session_state.practice_cat=cat; st.session_state.conv_history=[]; st.success('Loaded into Conversation Practice.')
    with tabs[1]:
        st.write('### People to know')
        st.caption('Type a person you keep hearing about. ChapLife will pull a quick visual/profile search so you can connect the face, name, and context.')
        person=st.text_input('Person’s name')
        if person:
            q=urllib.parse.quote(person)
            st.markdown(f"[See photos and profile for {person}](https://www.google.com/search?tbm=isch&q={q})")
            st.markdown(f"[Quick background on Wikipedia](https://en.wikipedia.org/w/index.php?search={q})")
            st.info('When ChapLife is hosted online, this panel can be upgraded to show the image and profile directly inside the app.')
    with tabs[2]:
        story=st.session_state.get('practice_story','Choose a story in Catch Me Up first')
        st.write('**Topic:** '+story)
        scenario=st.selectbox('Practice setting',['Coworker / everyday','Networking event','Romance / date','Friend group','Party / social event','Professional event','Someone I just met'])
        personality=st.selectbox('Conversation partner',['Random','Talkative','Quiet','Friendly','Reserved','Funny','Blunt','Distracted','Flirty','Professional','Intimidating'])
        coach=st.toggle('Coach while I practice',value=True)
        if 'conv_history' not in st.session_state: st.session_state.conv_history=[]
        if not st.session_state.conv_history:
            opener=f"Did you see what happened with {story}?" if story!='Choose a story in Catch Me Up first' else 'Did you see what everybody is talking about today?'
            st.session_state.conv_history=[('Them',opener)]
        for who,msg in st.session_state.conv_history: st.markdown(f'**{who}:** {msg}')
        reply=st.text_area('Your response',key='conv_reply')
        c1,c2,c3=st.columns(3)
        if c1.button('Send response',use_container_width=True):
            if reply.strip():
                score,tips=conversation_feedback(reply); st.session_state.conv_history.append(('You',reply.strip()))
                turn=len([x for x in st.session_state.conv_history if x[0]=='You'])
                followups=[f"Yeah. What part of {story} stood out to you?",'I get that. What do you think is going to happen next?','That makes sense. I had not thought about it that way—why do you say that?','Okay, switching gears a little—what have you been into lately?']
                st.session_state.conv_history.append(('Them',followups[(turn-1)%len(followups)]))
                st.session_state.last_conv_feedback=(score,tips); st.rerun()
        if c2.button('🛟 I’m stuck',use_container_width=True): st.info('Try: react to one thing they said → add one thought of your own → ask one open question.')
        if c3.button('End & review',use_container_width=True):
            yours=' '.join(m for w,m in st.session_state.conv_history if w=='You'); score,tips=conversation_feedback(yours)
            st.subheader('Conversation recap'); st.metric('Conversation score',f'{score}/10'); [st.write('• '+x) for x in tips]
            st.write(f"**Setting:** {scenario} • **Partner:** {personality}")
        if coach and st.session_state.get('last_conv_feedback'):
            score,tips=st.session_state.last_conv_feedback; st.caption('Coach note: '+tips[0])
        if st.button('Start a new conversation'): st.session_state.conv_history=[]; st.session_state.pop('last_conv_feedback',None); st.rerun()
    with tabs[3]:
        st.info('Conversation history and repeated-phrase tracking will grow as you practice. Growth Lab can use recurring weak spots for future exercises.')
        st.write('Skills: starting conversations • keeping them going • follow-up questions • sharing about yourself • opinions • networking • romance • group conversation • listening • natural exits • vocabulary variety')

# ---------- Career Simulator ----------
def sc(id,title,skill,level,prompt,best,why,bad1,bad2,bad3):
    return {'id':id,'title':title,'skill':skill,'level':level,'prompt':prompt,'choices':{best:10,bad1:4,bad2:2,bad3:0},'best':best,'why':why}

SCENARIOS=[
sc('RFI-001','Conflicting Outlet Heights','RFI Management','Beginner','Electrical drawings and architectural elevations show different outlet heights in Rooms 204–210. The electrician is waiting.','Create a clear RFI with both drawing references, route it, log it, and alert the PM/superintendent to the potential impact.','A traceable RFI avoids field assumptions and protects schedule/document control.','Send a casual text to the architect and wait.','Tell the electrician to use the electrical drawing.','Ignore it until the weekly meeting.'),
sc('SUB-002','Late Door Hardware Submittal','Submittals','Beginner','Door hardware submittal is due today; long-lead procurement depends on approval.','Follow up immediately, update the submittal log, identify schedule risk, and escalate if the promised date slips.','Submittal timing is tied directly to procurement and installation dates.','Wait two days, then follow up.','Remove it from the log until received.','Use a package from another project.'),
sc('DOC-003','Revision Arrives After Printing','Document Control','Beginner','A new drawing revision is issued after the field team printed yesterday’s set.','Upload and distribute the revision, mark superseded files, notify field leads, and confirm the current set is being used.','Using old drawings can create rework, cost, and claims.','Email the new sheet only to the PM.','Assume the superintendent saw the revision.','Do nothing because the old set is already printed.'),
sc('MIN-004','Meeting Minutes Disagreement','Meeting Minutes','Beginner','A subcontractor says your meeting minutes incorrectly assign them an action item.','Check your notes, confirm with the PM if needed, issue a correction or clarification, and keep the record factual.','Minutes are project records and should be accurate, neutral, and corrected transparently.','Delete the line without telling anyone.','Argue that the minutes are final.','Ignore their email.'),
sc('COI-005','Expired Insurance Certificate','Compliance','Beginner','A subcontractor is scheduled onsite tomorrow and their COI expired last week.','Flag it immediately, request compliant insurance documentation, and follow company/site requirements before work proceeds.','Insurance compliance is a prerequisite and should not be casually bypassed.','Let them work one day while they renew it.','Ask another subcontractor to cover them.','Delete the expiration reminder.'),
sc('PO-006','PO Amount Does Not Match Quote','Procurement','Beginner','A purchase order draft is $8,500 but the approved quote is $7,850.','Stop routing, verify scope/tax/allowances, correct the PO, and attach the supporting quote.','Small document mismatches become accounting and audit problems later.','Route it and correct it after signature.','Change the quote to match the PO.','Approve the higher amount just in case.'),
sc('CO-101','Owner Adds Conference Room Display','Change Orders','Intermediate','Owner asks the field team to add a large display plus power/data that is not in contract documents.','Document requested scope, identify cost/schedule impacts, and start the approved change process before extra work is authorized.','Added scope needs approval and traceability before cost is incurred.','Tell trades to proceed and price it later.','Use contingency without documentation.','Ignore it because the owner asked verbally.'),
sc('INV-102','Invoice Exceeds Field Progress','Cost Tracking','Intermediate','Subcontractor bills 90% complete; superintendent reports approximately 70%.','Flag the discrepancy, verify installed work/materials, coordinate corrected billing, and document approval.','Payment should match verified progress and contract terms.','Approve it to keep the subcontractor happy.','Change it to 70% yourself and pay it.','Reject the full invoice without review.'),
sc('SCH-103','Inspection Threatens Drywall','Scheduling','Intermediate','Framing inspection is not confirmed; drywall starts tomorrow.','Confirm inspection status now, alert PM/superintendent, protect the prerequisite, and assess downstream schedule impacts.','A missed prerequisite can stop work and cascade into multiple trades.','Let drywall start and hope the inspector comes.','Cancel the entire week immediately.','Wait to update the schedule after the delay occurs.'),
sc('MAT-104','Long-Lead Material Slips','Procurement','Intermediate','Manufacturer pushes switchgear delivery back four weeks.','Verify the new date, document it, notify the team, explore approved alternatives/sequence changes, and update procurement/schedule tracking.','Long-lead slippage requires early mitigation, not just a new date in a log.','Update the log and say nothing.','Ask the electrician to buy anything similar.','Wait until the original delivery date.'),
sc('RFI-105','RFI Response Changes Scope','RFI Management','Intermediate','Architect’s RFI answer requires additional backing that was not shown previously.','Distribute the response, identify potential change impact, coordinate pricing if needed, and update the RFI/change logs.','An RFI response can create cost/scope consequences that must be tracked.','Send it to the carpenter only.','Treat it as free work automatically.','File the response without notifying anyone.'),
sc('PAY-106','Lien Waiver Missing','Cost Tracking','Intermediate','A subcontractor pay application is otherwise ready, but required lien waiver documentation is missing.','Hold routing per company requirements, request the missing waiver, and document the outstanding item.','Payment controls exist to reduce legal and financial exposure.','Pay it and collect the waiver later.','Create a waiver yourself.','Ignore the requirement because the amount is small.'),
sc('PCH-107','Punch List Not Closing','Closeout','Intermediate','Several punch items are three weeks old and the owner walkthrough is approaching.','Assign owners/dates, follow up by trade, verify completion evidence, and escalate repeat misses.','Closeout needs active tracking so small items do not delay turnover.','Wait for trades to close items when convenient.','Mark items complete based on promises.','Delete old punch items.'),
sc('SUB-108','Substitution Request','Submittals','Intermediate','A subcontractor proposes a cheaper alternate material after the specified product was approved.','Require a formal substitution with technical/cost/schedule comparison and route it through the proper approval process.','Substitutions can affect design intent, warranty, cost, and schedule.','Approve it because it is cheaper.','Reject it without review.','Let the field decide.'),
sc('CCD-201','Field Directive Arrives','Change Management','Advanced','Architect issues a field directive that may add cost while the crew is mobilized.','Log and distribute the directive, confirm authorization path, capture labor/material impacts, and coordinate change documentation promptly.','Directives need fast field communication plus cost/scope traceability.','Tell crew to proceed with no records.','Wait for the monthly cost meeting.','Refuse to share it until a price is approved.'),
sc('CLM-202','Subcontractor Claims Delay','Claims / Documentation','Advanced','Subcontractor says another trade blocked access for six days and requests added cost.','Gather schedule, daily reports, photos, correspondence and access records; notify PM and document the claim without admitting responsibility.','Contemporaneous records are critical when evaluating delay claims.','Tell them they are wrong without checking.','Approve their requested cost immediately.','Delete emails that make the project look bad.'),
sc('BUD-203','Forecast Over Budget','Cost Tracking','Advanced','Forecast shows the project trending $185,000 over budget across multiple cost codes.','Validate commitments/forecast assumptions, identify drivers, prepare a clear variance summary, and coordinate corrective actions with the PM.','Good project controls explain the cause, not just the total.','Move costs to unrelated codes.','Wait until month-end.','Hide the variance until savings appear.'),
sc('LOG-204','Submittal/RFI Log Out of Sync','Document Control','Advanced','PM notices several returned submittals and answered RFIs are not reflected in your logs before an owner meeting.','Reconcile against the document platform, correct statuses/dates, flag discrepancies, and provide a verified summary.','Logs must be dependable before decisions are based on them.','Guess the missing dates.','Send the old log with a disclaimer.','Delete uncertain rows.'),
sc('INS-205','Failed Inspection','Inspections','Advanced','Firestopping inspection fails in two areas; ceiling closure is scheduled in 48 hours.','Document deficiencies, coordinate corrective work/reinspection, protect access, and update the short-term schedule and affected trades.','Closing work before correction/reinspection creates rework and compliance risk.','Close ceilings where possible and fix later.','Only tell the firestopping subcontractor.','Wait for the next inspection cycle.'),
sc('OWN-206','Owner Wants Earlier Turnover','Owner Coordination','Advanced','Owner asks to move turnover three weeks earlier with no reduction in scope.','Work with PM/superintendent to test feasibility, identify critical path/resources/cost impacts, and respond with documented options.','Acceleration must be analyzed; promising a date without a plan creates risk.','Promise the earlier date immediately.','Say no without analysis.','Tell every subcontractor to work overtime without approval.'),
sc('MOB-207','Trade Stacking Conflict','Field Coordination','Advanced','Mechanical, electrical and ceiling crews all plan to work in the same corridor tomorrow.','Coordinate with superintendent to sequence/zone the work, communicate the plan, and update the look-ahead.','Trade stacking hurts productivity and can create safety/quality conflicts.','Let them work it out onsite.','Cancel all three trades.','Give the corridor to whoever arrives first.'),
sc('CRS-301','Crisis: Water Leak + Owner Meeting','Crisis Day','Crisis','At 8:05 AM a water leak damages finished flooring. Your owner meeting is at 9:00 and the flooring subcontractor is asking who will pay.','First support site response/documentation, notify PM/superintendent, capture facts/photos, separate emergency mitigation from cost responsibility, then prepare a concise owner update.','In a crisis, protect people/property and facts first; do not assign blame before the situation is documented.','Focus on the 9:00 meeting and deal with leak later.','Tell flooring the plumber will pay.','Send a blame email to all trades.'),
sc('CRS-302','Crisis: Three Deadlines at Once','Crisis Day','Crisis','At 2:30 PM: a $220k pay app is due by 3:00, a critical RFI response just arrived, and tomorrow’s concrete pour lacks final inspection confirmation.','Triage by project risk: confirm the concrete prerequisite immediately, distribute/log the critical RFI, and coordinate the pay app deadline with the PM/accounting rather than silently rushing errors.','Priority is based on consequence and irreversibility, not simply which email arrived first.','Finish the pay app and ignore the rest until 3:00.','Forward all three to the PM with no summary.','Approve the pay app without checking so you have time.'),
sc('CRS-303','Crisis: Executive Walk + Missing Submittals','Crisis Day','Crisis','An executive site walk starts in 30 minutes. The PM asks for a current procurement risk list, but you discover five log statuses are wrong and two long-lead approvals are late.','Verify the critical items, clearly label what is confirmed vs pending, give the PM the top risks/actions, and finish full reconciliation after the walk.','Under pressure, accuracy with transparent limits is better than a polished but unreliable report.','Make the report look complete using estimated dates.','Tell the PM the log is unusable and provide nothing.','Hide the late items.'),
sc('CRS-304','Crisis: Subcontractor Walks Off','Crisis Day','Crisis','A major subcontractor stops work over a disputed change while their activity is on the critical path.','Notify PM/superintendent, document facts and contract/change status, identify immediate schedule impact and available mitigation, and keep communications professional.','Work stoppages can become claims; disciplined documentation and escalation matter.','Threaten the subcontractor by text.','Promise payment to get them back onsite.','Delete the disputed change from the log.'),
sc('CRS-305','Crisis: Bad News Before Client Call','Crisis Day','Crisis','Ten minutes before a client call, you learn a key delivery will miss the promised date by two weeks.','Verify the facts, alert the PM, prepare impact/mitigation options, and communicate the issue directly without minimizing or speculating.','Clients need timely facts plus a recovery plan.','Say nothing unless the client asks.','Blame the vendor immediately.','Tell the client the old date is still good.'),
]


def career_seed_day():
    """Seed incoming work as scheduled messages. A task appears when the request actually arrives."""
    state=sim_state()
    now=int(state["minutes"])

    seeded=[
        # msg key, arrival minute, sender, subject, body, task metadata
        ("M1",454,"Dana Lewis · Superintendent","Inspection confirmation needed",
         "Morning — I still do not have confirmation for the framing inspection. Drywall is supposed to start tomorrow. Can you chase this before 8:30?",
         "T1","Confirm framing inspection","Inspections","URGENT","08:30","Drywall is scheduled tomorrow. Confirmation has not been received."),

        ("M2",461,"Marcus Reed · Project Manager","OAC packet before 10 AM",
         "Please send me the current RFI/submittal logs and top procurement risks before the owner meeting. Flag anything you are not confident is current.",
         "T3","Prepare OAC meeting packet","Meetings","High","09:45","Current RFI log, submittal log, procurement risks and 3-week look-ahead."),

        ("M3",466,"Apex Electric · PM","RFI 017 holding Rooms 204–210",
         "We have two different outlet heights in the documents. Crew is moving to another area, but we need direction today.",
         "T2","Route RFI-017: outlet mounting heights","RFIs","High","09:15","Electrical is waiting on clarification between E-201 and A-402."),

        ("M4",472,"Accounting","Pay application cutoff today",
         "Apex Electric pay application must be approved or returned by 3:00 PM to make this cycle.",
         "T4","Review Apex Electric pay app","Cost","Medium","12:00","Pay app requests 90%; field report indicates roughly 70% installed."),

        ("M5",483,"Door Hardware Vendor","RE: Hardware package",
         "Factory slot may be lost if approved submittal is not released this week. Current quoted lead time is 10–12 weeks.",
         "T5","Follow up on door hardware submittal","Submittals","High","11:00","Long-lead hardware approval is late and may affect turnover."),

        ("M6",500,"Jasmine Cole · Accounting","Metro Interiors COI expires Friday",
         "Metro Interiors' Certificate of Insurance expires Friday. Please request the updated COI and update the compliance tracker when it comes in.",
         "T6","Update COI tracker","Compliance","Medium","15:00","Metro Interiors COI expires Friday.")
    ]

    for key,at,sender,subject,body,tkey,ttitle,tarea,tpriority,tdue,tdetail in seeded:
        existing_msg=rows("SELECT id FROM career_messages WHERE msg_key=?",(key,))
        existing_task=rows("SELECT id,status FROM career_tasks WHERE task_key=?",(tkey,))

        # Migration cleanup: a future request should not already be visible as a task/message.
        if now < at:
            if existing_msg:
                execute("DELETE FROM career_messages WHERE msg_key=?",(key,))
                existing_msg=[]
            if existing_task:
                execute("DELETE FROM career_tasks WHERE task_key=?",(tkey,))
                existing_task=[]

        if now >= at:
            if not existing_msg:
                execute("INSERT OR IGNORE INTO career_messages(msg_key,sender,subject,body,received_time) VALUES(?,?,?,?,?)",
                        (key,sender,subject,body,_career_time_from_minutes(at)))
                career_activity(state,"Incoming",subject,body)
            if not rows("SELECT id FROM career_tasks WHERE task_key=?",(tkey,)):
                execute("""INSERT OR IGNORE INTO career_tasks(task_key,title,area,priority,status,due_time,detail)
                           VALUES(?,?,?,?,?,?,?)""",(tkey,ttitle,tarea,tpriority,"Open",tdue,tdetail))
                career_activity(state,"New Task",ttitle,f"Created from {sender}'s { _career_time_from_minutes(at) } message.")
        else:
            rtype="Seed:"+key
            queued=rows("SELECT id FROM career_reaction_queue WHERE reaction_type=?",(rtype,))
            if not queued:
                execute("""INSERT INTO career_reaction_queue(
                    source_sent_id,due_minute,sender,subject,body,reaction_type,
                    task_key,task_title,task_area,task_priority,task_due_time,task_detail
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (None,at,sender,subject,body,rtype,tkey,ttitle,tarea,tpriority,tdue,tdetail))

def sim_state():
    state=get_setting("career_workday",None)
    if not state:
        state={"day":1,"minutes":448,"paused":False,"clocked_out":False,"project":"Fulton Commons Renovation","project_no":"FC-2417","phase":"MEP Rough-In","mode":"Training"}; set_setting("career_workday",state)
    return state

def save_sim(state): set_setting("career_workday",state)
def sim_time(state):
    h=state["minutes"]//60; m=state["minutes"]%60
    return f"{h%12 or 12}:{m:02d} {'AM' if h<12 else 'PM'}"
def advance_sim(state,mins=10):
    if not state["paused"] and not state["clocked_out"]:
        state["minutes"]=min(1020,state["minutes"]+mins)
        save_sim(state)
        career_process_reaction_queue(state)


TRAINING_GUIDES={
"RFI":{
"what":"An RFI (Request for Information) formally asks the design team to clarify missing, conflicting, or unclear contract information. An email can alert someone to the issue, but if the field needs formal design direction, the clarification should be captured in the RFI record.",
"steps":["Open Document Control below and verify the latest drawing/spec revision before drafting the RFI.","Use a short, searchable subject.","Reference the exact drawing/detail/spec and location.","Describe the conflict factually.","Ask one clear question; do not guess the design answer.","Route it to the proper design contact and copy the PM/Superintendent as required.","Log the response and distribute the clarification to the field."],
"example":'Subject: Receptacle mounting height — Rooms 204–210\nReferences: A-402 Interior Elevation 2 / E-201 Detail 3\nQuestion: A-402 indicates receptacles at 18" AFF while E-201 indicates 24" AFF in Rooms 204–210. Please confirm the required mounting height.',
"mistakes":"Vague questions, no drawing reference, multiple unrelated issues in one RFI, blame language, or telling the trade to guess."
},
"Project Email":{
"what":"Project email creates a traceable record of requests, decisions, distribution, and follow-up.",
"steps":["Use a specific subject.","Say why you are writing early.","Reference the project/document.","State the action needed and deadline.","CC only people who need action or visibility.","Verify attachments/revisions.","Follow up when a response is due."],
"example":"Subject: FC-2417 — RFI-017 response needed today\nAvery, please review RFI-017 regarding conflicting receptacle mounting heights on A-402 and E-201. Electrical rough-in in Rooms 204–210 is affected. Please respond by 2:00 PM if possible so the field can proceed.",
"mistakes":"Unclear requests, no deadline, unnecessary CCs, outdated attachments, or undocumented verbal decisions."
},
"Pay Application":{
"what":"A pay application requests payment for completed work and approved stored materials. Your review helps prevent unsupported billing.",
"steps":["Confirm contract/PO value.","Check prior payments.","Compare billed percent to field progress.","Verify approved changes.","Check retainage and required backup.","Flag discrepancies before approval.","Document what is still needed."],
"example":"If a line item is billed 80% complete while field verification supports about 55%, flag it and request support/correction before routing payment.",
"mistakes":"Approving because the math totals correctly. Correct arithmetic does not prove the work is billable."
},
"Meeting Minutes":{
"what":"Meeting minutes preserve decisions, commitments, responsible parties, and due dates.",
"steps":["Record attendees.","Capture decisions, not a transcript.","Turn commitments into action items.","Assign an owner and due date.","List unresolved items.","Distribute promptly.","Carry open actions forward."],
"example":"Action 04 — Apex Electric to confirm revised fixture lead time by Aug 26. Owner: Luis/Apex. Status: Open.",
"mistakes":"Writing only 'discussed schedule' without recording what was decided, who owns the action, or when it is due."
},
"Submittal":{
"what":"Submittals route contractor product/shop-drawing information for design review and must be tracked early enough to protect procurement.",
"steps":["Confirm spec section.","Check package completeness.","Log received date/revision.","Route to reviewer.","Track review due date.","Distribute returned disposition/comments.","Track procurement and long-lead impact."],
"example":"26 51 00-03 Interior LED Fixtures, Rev 0 — received from Apex Electric — route to Electrical Engineer; track return date before factory slot expires.",
"mistakes":"Treating an approval stamp as permission to ignore reviewer comments or failing to distribute the returned package."
}}

def training_box(topic,state):
    g=TRAINING_GUIDES[topic]
    with st.container(border=True):
        st.markdown(f"### 🎓 Training Assistant — {topic}")
        if state.get("mode")=="Training":
            st.info(g["what"])
            st.markdown("**How to complete it**")
            for i,x in enumerate(g["steps"],1): st.write(f"{i}. {x}")
            with st.expander("👀 Completed example",expanded=True): st.code(g["example"])
            st.warning("Common mistakes: "+g["mistakes"])
        elif state.get("mode")=="Assisted":
            st.caption("Hints are available. Open the permanent Training Library whenever you want the full workflow or example.")
        else:
            st.caption("Independent mode. The permanent Training Library is still available by choice.")

def career_activity(state,kind,title,detail=""):
    execute("INSERT INTO career_activity(activity_time,activity_type,title,detail) VALUES(?,?,?,?)",(sim_time(state),kind,title,detail))



def _career_clock_to_minutes(label):
    try:
        dt=datetime.strptime(label.strip(),"%I:%M %p")
        return dt.hour*60+dt.minute
    except:
        # Legacy seeded rows used 24-hour strings such as 07:34.
        try:
            h,m=label.strip().split(":")[:2]
            return int(h)*60+int(m)
        except:
            return 0

def _career_time_from_minutes(mins):
    h=mins//60; m=mins%60
    return f"{h%12 or 12}:{m:02d} {'AM' if h<12 else 'PM'}"

def _email_quality(subject,body):
    txt=(subject+" "+body).lower()
    score=0
    if len(subject.strip())>=8: score+=1
    if len(body.strip())>=45: score+=1
    if any(x in txt for x in ["please","can you","confirm","review","send","provide","advise","respond"]): score+=1
    if any(x in txt for x in ["today","by ","am","pm","deadline","before","due"]): score+=1
    if any(x in txt for x in ["rfi","drawing","a-","e-","spec","pay app","submittal","inspection","schedule","rooms"]): score+=1
    return score

def _queue_reaction(source_sent_id,due_minute,sender,subject,body,reaction_type="Reply",
                    task_key=None,task_title=None,task_area=None,task_priority=None,task_due_time=None,task_detail=None):
    execute("""INSERT INTO career_reaction_queue(
        source_sent_id,due_minute,sender,subject,body,reaction_type,
        task_key,task_title,task_area,task_priority,task_due_time,task_detail
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
    (source_sent_id,due_minute,sender,subject,body,reaction_type,
     task_key,task_title,task_area,task_priority,task_due_time,task_detail))


def career_role_redirect(recipient,subject,body):
    """Return a realistic redirect when the recipient is clearly outside the role needed for the request."""
    txt=(subject+" "+body).lower()

    # Strong intent signals only; ambiguous messages are allowed to play out naturally.
    design_request=(
        any(x in txt for x in ["clarify","clarification","confirm the required","design response","drawing conflict","conflicting drawing","rfi response"])
        and any(x in txt for x in ["drawing","rfi","a-","e-","spec","detail","receptacle","outlet"])
    )
    accounting_request=any(x in txt for x in ["payment run","pay application","pay app","invoice","billing","payment cutoff","process payment"])
    field_request=any(x in txt for x in ["field verify","verify in field","crew","framing inspection","rough-in","site condition","field condition","inspection confirmation"])
    hardware_request=any(x in txt for x in ["door hardware","hardware package","hardware submittal","factory slot"])
    coi_request=any(x in txt for x in ["coi","certificate of insurance","insurance certificate"])
    owner_request=any(x in txt for x in ["owner decision","owner approval","owner selection","owner change","client decision"])
    electrical_trade_request=any(x in txt for x in ["apex","electrical crew","electrical material","electrician","stored material"]) and not design_request

    # Marcus is a legitimate escalation/oversight path for almost everything, so don't flag PM mail as "wrong."
    if "Marcus Reed" in recipient:
        return None

    if design_request and "Avery Chen" not in recipient:
        return {
            "correct":"Avery Chen · Architect",
            "reason":"Design clarifications, drawing/spec conflicts, and formal RFI responses belong with the design team.",
            "copy":"Copy Marcus Reed (PM) and Dana Lewis (Superintendent) when the answer affects cost, schedule, or field work."
        }

    if accounting_request:
        # Asking the trade for backup is valid; asking PM for approval is valid. Obvious outsiders get redirected.
        if not any(x in recipient for x in ["Accounting","Marcus Reed","Apex Electric"]):
            return {
                "correct":"Jasmine Cole · Accounting / Marcus Reed · Project Manager",
                "reason":"Payment processing belongs with Accounting, while the PM owns project approval/authorization. If backup is missing, request it from Apex Electric.",
                "copy":"For a disputed pay app, keep Accounting, Marcus, and the affected subcontractor aligned."
            }

    if field_request and not any(x in recipient for x in ["Dana Lewis","Inspection Agency","Apex Electric"]):
        return {
            "correct":"Dana Lewis · Superintendent",
            "reason":"Field verification, crew sequencing, and site/inspection coordination are led from the field by the Superintendent.",
            "copy":"If an outside inspection confirmation is required, coordinate with the Inspection Agency and keep Dana copied."
        }

    if hardware_request and "Door Hardware Vendor" not in recipient:
        return {
            "correct":"Door Hardware Vendor",
            "reason":"Hardware lead time, factory slots, and vendor package status need to come from the hardware vendor.",
            "copy":"Copy Marcus if the lead time creates a schedule or turnover risk."
        }

    if coi_request and "Metro Interiors" not in recipient and "Accounting" not in recipient:
        return {
            "correct":"Metro Interiors",
            "reason":"The subcontractor/vendor must provide its current Certificate of Insurance. The project team tracks it but cannot issue it for them.",
            "copy":"Copy Accounting/project administration if they maintain the compliance record."
        }

    if owner_request and "Nia Brooks" not in recipient:
        return {
            "correct":"Nia Brooks · Owner Representative",
            "reason":"Owner selections, owner approvals, and client decisions need to come from the Owner Representative.",
            "copy":"Keep Marcus Reed copied so the PM can track cost/schedule consequences."
        }

    if electrical_trade_request and "Apex Electric" not in recipient:
        # If it is clearly a design clarification, design_request above wins.
        return {
            "correct":"Luis Ortega · Apex Electric PM",
            "reason":"Questions about Apex's manpower, electrical material, stored-material backup, or trade execution belong with the electrical subcontractor.",
            "copy":"Copy Dana for field coordination and Marcus for cost/schedule impact when appropriate."
        }

    return None

def career_schedule_email_reactions(state,sent_id,recipient,cc,subject,body):
    """Create realistic delayed reactions to an outgoing project email."""
    now=int(state["minutes"])
    txt=(subject+" "+body).lower()
    cc_txt=(cc or "").lower()
    quality=_email_quality(subject,body)

    # Process-awareness training: sometimes the recipient is correct, but email is the wrong formal process.
    # A drawing/spec conflict that requires documented design direction should be routed as an RFI.
    formal_design_issue=(
        any(x in txt for x in ["drawing conflict","conflicting drawing","conflicting drawings","spec conflict","clarification","confirm the required","which height","which dimension","design direction"])
        and any(x in txt for x in ["drawing","a-","e-","spec","detail","receptacle","outlet","dimension","rooms"])
    )
    looks_like_rfi_request=("rfi" not in txt or "submit rfi" not in txt) and formal_design_issue

    if "Avery Chen" in recipient and looks_like_rfi_request:
        reply=(
            "I can help with the design question, but this needs to be documented as a formal RFI rather than handled only by email. "
            "Please submit an RFI with the exact drawing/spec references, affected location, the conflict you found, and one clear question. "
            "Once it is routed, I can issue the design response against the RFI record."
        )
        if state.get("mode")=="Training":
            reply += " Training note: email can alert the architect that an issue exists, but the RFI creates the formal project record the field can rely on."
        _queue_reaction(
            sent_id,now+3,"Avery Chen · Architect","RE: "+(subject or "Design clarification"),reply,
            "Wrong Process",
            task_key=f"CREATE_RFI_{sent_id}",task_title="Create formal RFI for design clarification",
            task_area="RFIs",task_priority="URGENT",task_due_time=_career_time_from_minutes(now+20),
            task_detail="Your email reached the correct person, but the issue requires a formal RFI. Open the RFI Desk, reference the exact drawings/specs, describe the conflict, and ask one clear question."
        )
        career_activity(state,"Training","Email should have been an RFI","Correct recipient, wrong project-control process.")
        return

    # Role-awareness training: clearly misrouted emails are returned by the person you contacted.
    redirect=career_role_redirect(recipient,subject,body)
    if redirect:
        training_extra=""
        if state.get("mode")=="Training":
            training_extra=" Training note: "+redirect["reason"]+" "+redirect["copy"]
        reply=(
            "Hi — this one isn’t really in my lane. "
            +redirect["reason"]+
            " Please send this to **"+redirect["correct"]+"** instead. "
            +redirect["copy"]+
            training_extra
        )
        _queue_reaction(
            sent_id,now+3,recipient,"RE: "+(subject or "Your message"),reply,
            "Wrong Recipient",
            task_key=f"REROUTE_{sent_id}",task_title="Reroute email to the correct project contact",
            task_area="Communication",task_priority="High",task_due_time=_career_time_from_minutes(now+18),
            task_detail="Your original email was sent to the wrong role. Review the recipient's explanation, resend it to "+redirect["correct"]+", and use the CC guidance provided."
        )
        career_activity(state,"Training","Email routed to wrong role",f"{recipient} will redirect you to {redirect['correct']}.")
        return

    # Poor/unclear project email: recipient asks for clarification instead of magically knowing.
    if quality<=2:
        _queue_reaction(
            sent_id,now+5,recipient,"RE: "+(subject or "Your message"),
            "I saw your email, but I’m not clear on what you need from me. Can you send the specific document/location, requested action, and when you need the response?",
            "Clarification",
            task_key=f"EMAILCLARIFY_{sent_id}",task_title="Clarify outgoing email",
            task_area="Communication",task_priority="High",task_due_time=_career_time_from_minutes(now+25),
            task_detail="Recipient could not act on the original email. Rewrite it with a clear request, project reference, and deadline."
        )
        return

    # Architect / design-team behavior.
    if "Avery Chen" in recipient:
        if "rfi" in txt or "drawing" in txt or "receptacle" in txt or "outlet" in txt:
            _queue_reaction(sent_id,now+4,"Avery Chen · Architect","RE: "+subject,
                            "Received. I’m pulling the referenced sheets now. I’ll confirm whether this can be answered directly or needs a formal RFI revision.",
                            "Acknowledgment")
            if any(x in txt for x in ["a-402","e-201","18","24","rooms 204","rooms 204–210"]):
                _queue_reaction(sent_id,now+18,"Avery Chen · Architect","RE: "+subject,
                                'I reviewed A-402 and E-201. Use 18" AFF in Rooms 204–210. I’ll carry the clarification into the next bulletin. Please make sure the field team receives this response.',
                                "Design Response",
                                task_key=f"DISTRIBUTE_{sent_id}",task_title="Distribute architect clarification to field",
                                task_area="RFIs",task_priority="URGENT",task_due_time=_career_time_from_minutes(now+30),
                                task_detail='Architect answered the mounting-height conflict. Send the clarification to Dana/Apex and update the RFI log.')
            else:
                _queue_reaction(sent_id,now+16,"Avery Chen · Architect","RE: "+subject,
                                "I need the exact drawing/detail references and affected rooms before I can issue a response. Please revise the request and resend.",
                                "Revision Request",
                                task_key=f"REVISION_{sent_id}",task_title="Revise design clarification request",
                                task_area="RFIs",task_priority="High",task_due_time=_career_time_from_minutes(now+35),
                                task_detail="Architect needs exact references/location before responding.")
        else:
            _queue_reaction(sent_id,now+9,"Avery Chen · Architect","RE: "+subject,
                            "Received. Can you confirm which drawing/spec section this relates to so I can route it to the right person?",
                            "Follow-up")

    # Superintendent behavior: field-focused, direct, time-sensitive.
    elif "Dana Lewis" in recipient:
        if any(x in txt for x in ["inspection","field","rfi","rough-in","electrical","framing"]):
            _queue_reaction(sent_id,now+3,"Dana Lewis · Superintendent","RE: "+subject,
                            "Got it. I’ll hold the affected crew/area until we have documented direction. Send me the RFI/confirmation number as soon as you have it.",
                            "Field Response")
            _queue_reaction(sent_id,now+20,"Dana Lewis · Superintendent","Field status follow-up",
                            "Any update? The crew is about to run out of work in the alternate area. I need to know whether we can release Rooms 204–210.",
                            "Pressure Follow-up",
                            task_key=f"FIELDUPDATE_{sent_id}",task_title="Give Superintendent field-status update",
                            task_area="Field Coordination",task_priority="URGENT",task_due_time=_career_time_from_minutes(now+30),
                            task_detail="Dana is waiting on direction before releasing the crew.")
        else:
            _queue_reaction(sent_id,now+6,"Dana Lewis · Superintendent","RE: "+subject,
                            "Copy. Tell me what you need verified in the field and I’ll get you an answer.",
                            "Reply")

    # PM behavior: prioritization, accountability, documentation.
    elif "Marcus Reed" in recipient:
        if "status" in txt or "update" in txt or "rfi" in txt:
            _queue_reaction(sent_id,now+5,"Marcus Reed · Project Manager","RE: "+subject,
                            "Thanks. Keep the RFI and field impact tied together in the update. If the architect doesn’t respond by the time you promised, follow up before it becomes tomorrow’s schedule problem.",
                            "PM Coaching")
        elif "pay" in txt or "cost" in txt or "billing" in txt:
            _queue_reaction(sent_id,now+5,"Marcus Reed · Project Manager","RE: "+subject,
                            "Good. Do not release the pay app until the billed percentage is supported. Document the discrepancy and copy Accounting on the resolution.",
                            "PM Direction",
                            task_key=f"COSTFOLLOW_{sent_id}",task_title="Document pay-app resolution",
                            task_area="Cost",task_priority="High",task_due_time=_career_time_from_minutes(now+45),
                            task_detail="PM wants documented support/correction before payment is released.")
        else:
            _queue_reaction(sent_id,now+7,"Marcus Reed · Project Manager","RE: "+subject,
                            "Received. What is the project impact and what do you recommend as the next coordination step?",
                            "PM Follow-up",
                            task_key=f"PMFOLLOW_{sent_id}",task_title="Respond to PM with impact + next step",
                            task_area="Coordination",task_priority="High",task_due_time=_career_time_from_minutes(now+35),
                            task_detail="PM expects you to connect the issue to cost/schedule/field impact and propose the next coordination action.")

    # Subcontractor behavior: practical, may push for quick direction / payment.
    elif "Apex Electric" in recipient:
        if "pay" in txt or "billing" in txt or "percent" in txt:
            _queue_reaction(sent_id,now+6,"Luis Ortega · Apex Electric PM","RE: "+subject,
                            "We billed 90% because material is onsite and rough-in is substantially complete in the released areas. I can send the stored-material backup and marked-up progress plan. Tell me which line item you’re holding.",
                            "Subcontractor Pushback")
            _queue_reaction(sent_id,now+17,"Luis Ortega · Apex Electric PM","Apex backup uploaded",
                            "I sent the stored-material invoice and progress markup. Please confirm whether Accounting can keep the undisputed portion moving this cycle.",
                            "Backup Received",
                            task_key=f"APEXBACKUP_{sent_id}",task_title="Review Apex backup and separate disputed amount",
                            task_area="Cost",task_priority="High",task_due_time=_career_time_from_minutes(now+40),
                            task_detail="Apex supplied backup and is asking whether the undisputed portion can proceed.")
        elif "rfi" in txt or "outlet" in txt or "receptacle" in txt:
            _queue_reaction(sent_id,now+4,"Luis Ortega · Apex Electric PM","RE: "+subject,
                            "Understood. We moved the crew to the west side for now. Please send the architect response as soon as it lands so we don’t lose the afternoon.",
                            "Trade Response")
        else:
            _queue_reaction(sent_id,now+8,"Luis Ortega · Apex Electric PM","RE: "+subject,
                            "Received. I’ll check with the foreman and get back to you.",
                            "Acknowledgment")

    elif "Door Hardware Vendor" in recipient:
        if any(x in txt for x in ["hardware","submittal","factory","lead time"]):
            _queue_reaction(sent_id,now+6,"Door Hardware Vendor","RE: "+subject,
                            "Thanks for checking in. The factory slot is still being held, but we need the approved hardware release this week to protect the current lead time.",
                            "Vendor Response")
        else:
            _queue_reaction(sent_id,now+5,"Door Hardware Vendor","RE: "+subject,
                            "I’m the hardware vendor, so I can help with the hardware package, fabrication, and lead-time questions. This request looks like it belongs with the project team or another trade.",
                            "Role Clarification")

    elif "Metro Interiors" in recipient:
        if any(x in txt for x in ["coi","insurance","drywall","interiors"]):
            _queue_reaction(sent_id,now+6,"Metro Interiors","RE: "+subject,
                            "Received. I’ll have our office send the current COI and confirm the drywall coordination item.",
                            "Subcontractor Response")
        else:
            _queue_reaction(sent_id,now+5,"Metro Interiors","RE: "+subject,
                            "This doesn’t appear to involve our interiors scope. Please check the responsible trade/project contact.",
                            "Role Clarification")

    elif "Inspection Agency" in recipient:
        if "inspection" in txt:
            _queue_reaction(sent_id,now+7,"Inspection Agency","RE: "+subject,
                            "We have the request. I’m checking the inspector schedule and will send confirmation once the slot is assigned.",
                            "Inspection Response")
            _queue_reaction(sent_id,now+18,"Inspection Agency","Framing inspection confirmed",
                            "Framing inspection is confirmed for 8:00 AM tomorrow. Please ensure the area is accessible and ready before the inspector arrives.",
                            "Inspection Confirmation",
                            task_key=f"INSPECTDIST_{sent_id}",task_title="Distribute framing inspection confirmation",
                            task_area="Inspections",task_priority="High",task_due_time=_career_time_from_minutes(now+28),
                            task_detail="Send the confirmed inspection time to Dana and the affected field team.")
        else:
            _queue_reaction(sent_id,now+5,"Inspection Agency","RE: "+subject,
                            "We only handle inspection scheduling/confirmation. This request should go back to the appropriate project team member.",
                            "Role Clarification")

    elif "Nia Brooks" in recipient:
        if any(x in txt for x in ["owner","selection","approval","decision","change"]):
            _queue_reaction(sent_id,now+10,"Nia Brooks · Owner Representative","RE: "+subject,
                            "Thanks. I’m reviewing this from the owner side. Please make sure Marcus is included on any cost or schedule impact before I confirm the decision.",
                            "Owner Response")
        else:
            _queue_reaction(sent_id,now+7,"Nia Brooks · Owner Representative","RE: "+subject,
                            "I represent the owner, so I’m usually the right contact for owner decisions and approvals. This looks more like contractor/design coordination; please route it through Marcus or the responsible project contact.",
                            "Role Clarification")

    # Accounting behavior: process/backup focused.
    elif "Accounting" in recipient:
        if "pay" in txt or "billing" in txt or "apex" in txt:
            _queue_reaction(sent_id,now+5,"Jasmine Cole · Accounting","RE: "+subject,
                            "I placed the pay application on hold. Please send the PM-approved amount and any revised backup by 2:30 PM if you want it included in today’s payment run.",
                            "Accounting Hold",
                            task_key=f"ACCT_{sent_id}",task_title="Send Accounting approved pay-app amount",
                            task_area="Cost",task_priority="High",task_due_time="2:30 PM",
                            task_detail="Accounting needs the approved/revised amount and backup before the payment-run cutoff.")
        else:
            _queue_reaction(sent_id,now+7,"Jasmine Cole · Accounting","RE: "+subject,
                            "Received. Please attach the supporting document or reference the PO/subcontract number so I can process it.",
                            "Documentation Request")

    # CC consequences and cross-talk.
    issue_is_field=any(x in txt for x in ["rfi","field","electrical","inspection","rough-in","framing"])
    if issue_is_field and "dana" not in cc_txt and "Dana Lewis" not in recipient:
        _queue_reaction(sent_id,now+14,"Dana Lewis · Superintendent","Why wasn’t field copied?",
                        "I heard this issue was already sent out. Please include me on anything that is holding field work so I’m not finding out secondhand.",
                        "CC Consequence")
    if ("pay" in txt or "billing" in txt or "cost" in txt) and "accounting" not in cc_txt and "Accounting" not in recipient:
        _queue_reaction(sent_id,now+22,"Jasmine Cole · Accounting","Pay-app status?",
                        "Marcus mentioned there may be a billing hold. Please copy Accounting on the documented resolution so we don’t miss the cutoff.",
                        "CC Consequence")

def career_process_reaction_queue(state):
    due=rows("SELECT * FROM career_reaction_queue WHERE due_minute<=? ORDER BY due_minute,id",(int(state["minutes"]),))
    for q in due:
        rtype=q["reaction_type"] or ""

        # Conditional reminders/escalations disappear silently if the related task was completed early.
        if rtype.startswith("COND["):
            close=rtype.find("]")
            cond_key=rtype[5:close] if close>5 else ""
            if cond_key:
                task=rows("SELECT status FROM career_tasks WHERE task_key=?",(cond_key,))
                if task and task[0]["status"]=="Done":
                    career_activity(state,"Prevented Reminder",q["subject"],f"No message sent because {cond_key} was already completed.")
                    execute("DELETE FROM career_reaction_queue WHERE id=?",(q["id"],))
                    continue

        key=f"AUTO_{q['id']}"
        if not rows("SELECT id FROM career_messages WHERE msg_key=?",(key,)):
            execute("INSERT INTO career_messages(msg_key,sender,subject,body,received_time) VALUES(?,?,?,?,?)",
                    (key,q["sender"],q["subject"],q["body"],_career_time_from_minutes(q["due_minute"])))
            career_activity(state,"Incoming",q["subject"],q["body"])
            if q["task_key"]:
                execute("""INSERT OR IGNORE INTO career_tasks(task_key,title,area,priority,status,due_time,detail)
                           VALUES(?,?,?,?,?,?,?)""",
                        (q["task_key"],q["task_title"],q["task_area"],q["task_priority"],"Open",q["task_due_time"],q["task_detail"]))
                if q["reaction_type"] and str(q["reaction_type"]).startswith("Seed:"):
                    career_activity(state,"New Task",q["task_title"],f"Created from the incoming {q['subject']} message.")
        execute("DELETE FROM career_reaction_queue WHERE id=?",(q["id"],))

def career_reactions(state):
    """Timed project events only fire when they are still relevant."""
    mins=int(state["minutes"])

    def task_open(key):
        r=rows("SELECT status FROM career_tasks WHERE task_key=?",(key,))
        return bool(r) and r[0]["status"]!="Done"

    def send_once(key,at,sender,subject,body):
        if mins>=at and not rows("SELECT id FROM career_messages WHERE msg_key=?",(key,)):
            execute("INSERT INTO career_messages(msg_key,sender,subject,body,received_time) VALUES(?,?,?,?,?)",
                    (key,sender,subject,body,_career_time_from_minutes(at)))
            career_activity(state,"Incoming",subject,body)

    # 9:00 field reminder only if the RFI work is still unresolved.
    if task_open("T2"):
        send_once("EV900",540,"Dana Lewis · Superintendent","9:00 field follow-up",
                  "I still need the RFI number for the outlet-height conflict before electrical returns to Rooms 204–210.")

    # 9:45 meeting reminder reflects only unfinished prep items.
    if mins>=585 and not rows("SELECT id FROM career_messages WHERE msg_key='EV945'"):
        missing=[]
        if task_open("T3"): missing.append("OAC packet")
        if task_open("T2"): missing.append("RFI status")
        if task_open("T4"): missing.append("Apex billing review")
        if missing:
            send_once("EV945",585,"Marcus Reed · Project Manager","OAC meeting in 15 minutes",
                      "Before the 10:00 meeting, I still need: "+", ".join(missing)+". Please tighten up what is still open.")
        else:
            career_activity(state,"Prevented Reminder","OAC meeting reminder suppressed","All related preparation was completed before 9:45.")

    # No generic architect chase if the RFI task has already been completed/routed.
    if task_open("T2"):
        send_once("EV1030",630,"Avery Chen · Architect","RE: RFI-017",
                  "I still don't see a complete RFI with the drawing references. If you route it, I can review the clarification.")

    # Before-lunch status appears only if actual morning work remains open.
    if mins>=705 and not rows("SELECT id FROM career_messages WHERE msg_key='EV1145'"):
        open_items=[]
        for k,label in [("T1","inspection"),("T2","RFI"),("T3","OAC packet"),("T4","pay app"),("T5","hardware submittal")]:
            if task_open(k): open_items.append(label)
        if open_items:
            send_once("EV1145",705,"Marcus Reed · Project Manager","Before lunch status",
                      "Before lunch, send me the status of the items still open: "+", ".join(open_items)+".")
        else:
            career_activity(state,"Prevented Reminder","Before-lunch status suppressed","Morning work was already completed.")



def career_queue_message(state,delay,sender,subject,body,reaction_type="Project Reaction",
                         task_key=None,task_title=None,task_area=None,task_priority=None,task_due_time=None,task_detail=None,
                         cancel_if_done=None):
    stored_type=f"COND[{cancel_if_done}]::{reaction_type}" if cancel_if_done else reaction_type
    _queue_reaction(
        None,int(state["minutes"])+delay,sender,subject,body,stored_type,
        task_key,task_title,task_area,task_priority,task_due_time,task_detail
    )

def career_has_evidence(task_key):
    """Check the simulator records that should exist before selected tasks are truly complete."""
    if task_key=="T2":
        return bool(rows("SELECT id FROM career_rfis"))
    if task_key=="T4":
        return bool(rows("SELECT id FROM career_activity WHERE activity_type='Cost Review'"))
    if task_key=="T3":
        return bool(rows("SELECT id FROM career_sent WHERE lower(subject) LIKE '%oac%' OR lower(body) LIKE '%oac%'"))
    if task_key=="T1":
        return bool(rows("SELECT id FROM career_sent WHERE lower(subject) LIKE '%inspection%' OR lower(body) LIKE '%inspection%'"))
    if task_key=="T5":
        return bool(rows("SELECT id FROM career_sent WHERE lower(subject) LIKE '%hardware%' OR lower(body) LIKE '%hardware%' OR lower(body) LIKE '%submittal%'"))
    if task_key=="T6":
        return bool(rows("SELECT id FROM career_sent WHERE lower(subject) LIKE '%coi%' OR lower(body) LIKE '%insurance%' OR lower(body) LIKE '%certificate%'"))
    return True

def career_task_status_reaction(state,t,old_status,new_status):
    key=t["task_key"]; title=t["title"]
    career_activity(state,"Task Status",f"{title}: {old_status} → {new_status}",f"Priority {t['priority']} · Due {t['due_time']}")

    if new_status=="In Progress":
        if t["priority"]=="URGENT":
            career_queue_message(state,7,"Marcus Reed · Project Manager","Status check — "+title,
                                 "I see you picked this up. What is the blocker, who owns the next response, and when should I expect an update?",
                                 "PM Status Check",cancel_if_done=key)
        elif key=="T4":
            career_queue_message(state,9,"Jasmine Cole · Accounting","Apex pay app timing",
                                 "Thanks for picking this up. Reminder: I need a supported amount before the payment-run cutoff.",
                                 "Deadline Reminder",cancel_if_done=key)
        else:
            career_queue_message(state,12,"Marcus Reed · Project Manager","RE: "+title,
                                 "Thanks. Keep the task status current and document the outcome when you close it.",
                                 "PM Coaching",cancel_if_done=key)

    elif new_status=="Waiting":
        # Waiting without communication is not enough.
        related=rows("SELECT id FROM career_sent WHERE sent_time>=? ORDER BY id DESC LIMIT 1",(sim_time(state),))
        career_queue_message(state,10,"Marcus Reed · Project Manager","Waiting status — "+title,
                             "Who are we waiting on, when did you contact them, and when are you following up? 'Waiting' still needs an owner and a next-action time.",
                             "Waiting Follow-up",
                             task_key=f"WAITFOLLOW_{key}_{state['minutes']}",task_title="Set follow-up for "+title,
                             task_area=t["area"],task_priority="High",task_due_time=_career_time_from_minutes(int(state["minutes"])+30),
                             task_detail="Document who owns the response and perform a follow-up if it has not arrived.",
                             cancel_if_done=key)

    elif new_status=="Done":
        if not career_has_evidence(key):
            # Reject false completion and reopen.
            execute("UPDATE career_tasks SET status='In Progress',completed_at=NULL WHERE id=?",(t["id"],))
            career_queue_message(state,2,"Marcus Reed · Project Manager","Task reopened — "+title,
                                 "I saw this was marked Done, but I can’t find the supporting project action/documentation. I reopened it. Complete the actual work, then close the task.",
                                 "Completion Rejected")
            career_activity(state,"Quality Control",title+" reopened","Marked Done without required supporting evidence.")
            return "reopened"

        # Remove any pending reminders that existed only because this task had not been completed yet.
        queued=rows("SELECT id,reaction_type FROM career_reaction_queue")
        for q in queued:
            if (q["reaction_type"] or "").startswith(f"COND[{key}]"):
                execute("DELETE FROM career_reaction_queue WHERE id=?",(q["id"],))

        if key=="T2":
            career_queue_message(state,5,"Dana Lewis · Superintendent","RFI routed — field needs the response",
                                 "Thanks. I see the RFI is out. Keep me posted when design answers; electrical is still working around the affected rooms.",
                                 "Field Reaction")
        elif key=="T4":
            career_queue_message(state,4,"Jasmine Cole · Accounting","Apex review received",
                                 "I see the cost review is complete. I’ll keep the disputed amount on hold until the approved backup/correction is documented.",
                                 "Accounting Reaction")
        elif key=="T3":
            career_queue_message(state,5,"Marcus Reed · Project Manager","OAC packet received",
                                 "Got it. I’m reviewing the packet now. If any log is stale, flag it before the meeting rather than letting the owner discover it.",
                                 "PM Review")
        elif key=="T1":
            career_queue_message(state,4,"Dana Lewis · Superintendent","Inspection follow-up",
                                 "Thanks for chasing it. I still need the actual confirmation before I release tomorrow’s drywall sequence.",
                                 "Field Follow-up")
        elif key=="T5":
            career_queue_message(state,8,"Door Hardware Vendor","RE: Hardware package",
                                 "Thanks for the follow-up. The factory slot is still being held temporarily. We need the approved release this week to protect the quoted lead time.",
                                 "Vendor Reaction")
        else:
            career_queue_message(state,8,"Marcus Reed · Project Manager","Completed — "+title,
                                 "I see this closed. Make sure the final record is filed where the team can find it.",
                                 "Completion Acknowledgment")

    elif new_status=="Open" and old_status in ("In Progress","Waiting"):
        career_queue_message(state,10,"Marcus Reed · Project Manager","Task moved back to Open — "+title,
                             "I noticed this moved back to Open. Add a note or communicate the reason if the priority, owner, or plan changed.",
                             "Status Regression")

    return "ok"


def reset_career_simulation():
    """Reset the entire Career Simulator to a fresh Day 1 without touching the rest of ChapLife."""
    for tbl in [
        "career_tasks","career_messages","career_sent","career_activity",
        "career_rfis","career_notes","career_log","career_reaction_queue"
    ]:
        reset_table(tbl)
    # Remove saved workday state so sim_state() rebuilds the original morning.
    execute("DELETE FROM settings WHERE key IN (?,?)",("career_workday","career_scenario"))
    # Clear related session-state notices/selections so old UI state does not bleed into the new run.
    for k in list(st.session_state.keys()):
        if k.startswith(("career_","result_","choice_","stat_")):
            try: del st.session_state[k]
            except: pass

def career():
    state=sim_state(); career_seed_day(); career_process_reaction_queue(state); career_reactions(state)
    st.markdown(f"<div class='hero'><h1>🏗️ Northline Construction · Project Hub</h1><p><b>{state['project']}</b> · {state['project_no']} · {state['phase']} · Simulated Day {state['day']}</p></div>",unsafe_allow_html=True)
    top=st.columns(4); top[0].metric("Simulated time",sim_time(state)); top[1].metric("Unread",rows("SELECT COUNT(*) n FROM career_messages WHERE read=0")[0]["n"]); top[2].metric("Open tasks",rows("SELECT COUNT(*) n FROM career_tasks WHERE status!='Done'")[0]["n"]); top[3].metric("Mode",state["mode"])
    if state["paused"]:
        st.warning("⏸️ WORKDAY PAUSED — project time, deadlines and interruptions are frozen.")
        with st.container(border=True):
            st.subheader("Where I left off"); st.write(f"**{state['project']} · Day {state['day']} · {sim_time(state)}**")
            for t in rows("SELECT * FROM career_tasks WHERE status!='Done' ORDER BY CASE priority WHEN 'URGENT' THEN 0 WHEN 'High' THEN 1 ELSE 2 END, due_time LIMIT 4"): st.write(f"• {t['priority']} — {t['title']} · due {t['due_time']}")
        if st.button("▶ Resume Workday",type="primary",use_container_width=True): state["paused"]=False; save_sim(state); st.rerun()
        if st.button("🏠 Save & Exit to ChapLife",use_container_width=True): goto("Home"); st.rerun()
        return
    controls=st.columns(6)
    if controls[0].button("⏸ Pause Workday",use_container_width=True): state["paused"]=True; save_sim(state); st.rerun()
    if controls[1].button("💾 Save & Exit",use_container_width=True): save_sim(state); goto("Home"); st.rerun()
    if controls[2].button("⏩ Work 10 Min",use_container_width=True):
        advance_sim(state,10); career_reactions(state); st.rerun()
    if controls[3].button("🕔 Clock Out",use_container_width=True): state["clocked_out"]=True; save_sim(state); st.success("Workday saved. Unfinished work remains for your next simulated day.")
    reset_clicked=controls[4].button("🔄 Reset Simulation",use_container_width=True)
    mode=controls[5].selectbox("Assistance",["Training","Assisted","Independent"],index=["Training","Assisted","Independent"].index(state.get("mode","Training")),label_visibility="collapsed")
    if reset_clicked:
        st.session_state["confirm_full_career_reset"]=True
    if mode!=state.get("mode"): state["mode"]=mode; save_sim(state)

    if st.session_state.get("confirm_full_career_reset"):
        with st.container(border=True):
            st.error("Reset the ENTIRE Career Simulator?")
            st.write("This will erase the simulated workday, inbox, sent mail, tasks, RFIs, cost/career activity, scenario results, queued reactions, training notes, and simulator progress. **The rest of ChapLife will not be changed.**")
            c=st.columns(2)
            if c[0].button("Yes — Reset Career Simulator",type="primary",use_container_width=True,key="career_reset_yes"):
                reset_career_simulation()
                st.session_state["page"]="Career Simulator"
                st.session_state["career_reset_done"]=True
                st.rerun()
            if c[1].button("Cancel",use_container_width=True,key="career_reset_cancel"):
                st.session_state["confirm_full_career_reset"]=False
                st.rerun()
        return

    if st.session_state.get("career_reset_done"):
        st.success("✅ Career Simulator reset. You are starting fresh from Day 1.")
        st.session_state["career_reset_done"]=False

    tabs=st.tabs(["🖥️ Today","📧 Inbox","✅ Tasks","📄 RFI Desk","💵 Cost Desk","📅 Calendar","👥 Team","📚 Training Library","🔥 Scenario Lab","📈 Performance"])
    with tabs[0]:
        st.subheader("Monday Morning · Project Command Center")
        st.caption("Work enters your queue when requests/messages arrive. If you finish an item before a scheduled reminder, that reminder is suppressed.")
        c=st.columns(3)
        c[0].error("🔴 2 urgent — Inspection + RFI holding field work")
        c[1].warning("🟠 4 due today — OAC packet · pay app · submittal follow-up")
        c[2].info("📅 10:00 AM OAC Meeting — Owner + architect + project team")
        st.markdown("#### Priority board")
        for t in rows("SELECT * FROM career_tasks WHERE status!='Done' ORDER BY CASE priority WHEN 'URGENT' THEN 0 WHEN 'High' THEN 1 ELSE 2 END, due_time"):
            with st.container(border=True):
                st.markdown(f"**{t['title']}** · {t['priority']} · due {t['due_time']} — {t['detail']}")
        if state["mode"]=="Training": st.info("Training tip: prioritize by consequence. A prerequisite that can stop field work may outrank an administrative deadline that can be coordinated.")
        st.markdown("#### Live project activity")
        recent=rows("SELECT * FROM career_activity ORDER BY id DESC LIMIT 12")
        if not recent:
            st.caption("Your submissions and project reactions will appear here.")
        for a in recent:
            with st.container(border=True):
                st.markdown(f"**{a['activity_time']} · {a['activity_type']} — {a['title']}**")
                if a['detail']: st.caption(a['detail'])
    with tabs[1]:
        st.subheader("Project Inbox")
        pending=rows("SELECT * FROM career_reaction_queue ORDER BY due_minute,id")
        if pending:
            st.caption(f"Project activity is live • {len(pending)} future response/follow-up event{'s' if len(pending)!=1 else ''} are scheduled but will stay hidden until simulated time reaches them.")
        else:
            st.caption("Only messages that have actually arrived by the current simulated time appear here.")
        visible_messages=[
            m for m in rows("SELECT * FROM career_messages ORDER BY id DESC")
            if _career_clock_to_minutes(m["received_time"]) <= int(state["minutes"])
        ]
        if not visible_messages:
            st.info(f"No messages have arrived yet at {sim_time(state)}. Incoming email will populate as simulated time moves.")
        for m in visible_messages:
            icon="●" if not m["read"] else "○"
            with st.expander(f"{icon} {m['received_time']} · {m['sender']} — {m['subject']}"):
                execute("UPDATE career_messages SET read=1 WHERE id=?",(m["id"],))
                st.write(m["body"])
        training_box("Project Email",state)
        rfi_needed=rows("SELECT * FROM career_tasks WHERE task_key LIKE 'CREATE_RFI_%' AND status!='Done' ORDER BY id DESC LIMIT 1")
        if rfi_needed:
            with st.container(border=True):
                st.warning("📄 A formal RFI is required for your current design question.")
                st.write(rfi_needed[0]["detail"])
                if st.button("Open RFI Desk →",use_container_width=True,key="jump_to_rfi_from_email"):
                    st.session_state["career_jump_rfi"]=True
                    st.info("Use the **RFI Desk** tab above to complete the formal request.")
        st.markdown("#### Compose / reply")
        with st.form("career_compose",clear_on_submit=True):
            recipient=st.selectbox("To",[
                "Marcus Reed · Project Manager",
                "Dana Lewis · Superintendent",
                "Avery Chen · Architect",
                "Nia Brooks · Owner Representative",
                "Apex Electric",
                "Door Hardware Vendor",
                "Metro Interiors",
                "Inspection Agency",
                "Accounting"
            ])
            cc=st.multiselect("CC",[
                "Marcus Reed · Project Manager",
                "Dana Lewis · Superintendent",
                "Avery Chen · Architect",
                "Nia Brooks · Owner Representative",
                "Apex Electric",
                "Door Hardware Vendor",
                "Metro Interiors",
                "Inspection Agency",
                "Accounting"
            ])
            subject=st.text_input("Subject")
            body=st.text_area("Message",height=130)
            sent=st.form_submit_button("Send Email",use_container_width=True)
            if sent:
                sent_id=execute("INSERT INTO career_sent(sent_time,recipient,cc,subject,body) VALUES(?,?,?,?,?)",(sim_time(state),recipient,", ".join(cc),subject,body))
                career_activity(state,"Email","Email sent — "+(subject or "No subject"),"To "+recipient+" | CC: "+(", ".join(cc) if cc else "none"))
                career_schedule_email_reactions(state,sent_id,recipient,", ".join(cc),subject,body)
                sent_at=sim_time(state)
                advance_sim(state,8)
                career_reactions(state)
                st.session_state["career_sent_ok"]=f"✓ SENT at {sent_at}. It is saved in Sent Mail. The project is continuing to react as simulated time moves."
        if st.session_state.get("career_sent_ok"): st.success(st.session_state.pop("career_sent_ok"))
        sentmail=rows("SELECT * FROM career_sent ORDER BY id DESC LIMIT 10")
        if sentmail:
            st.markdown("#### Sent Mail")
            for x in sentmail:
                with st.expander(f"✓ {x['sent_time']} · {x['subject'] or '(No subject)'} → {x['recipient']}"):
                    st.write(x["body"]); st.caption("CC: "+(x["cc"] or "none"))
    with tabs[2]:
        st.subheader("My Work Queue")
        for t in rows("SELECT * FROM career_tasks ORDER BY due_time"):
            with st.container(border=True):
                a,b=st.columns([5,1]); a.markdown(f"**{t['title']}** · {t['area']} · {t['priority']} · Due {t['due_time']} — {t['detail']}"); opts=["Open","In Progress","Waiting","Done"]; new=b.selectbox("Status",opts,index=opts.index(t["status"]),key="stat_"+t["task_key"],label_visibility="collapsed")
                if new!=t["status"]:
                    old_status=t["status"]
                    execute("UPDATE career_tasks SET status=?,completed_at=? WHERE id=?",(new,sim_time(state) if new=="Done" else None,t["id"]))
                    outcome=career_task_status_reaction(state,t,old_status,new)
                    advance_sim(state,6)
                    career_reactions(state)
                    if outcome=="reopened":
                        st.session_state["task_reaction_notice"]="⚠️ The task was reopened because the simulator could not find the work required to support completion."
                    st.rerun()
        if st.session_state.get("task_reaction_notice"):
            st.warning(st.session_state.pop("task_reaction_notice"))
    with tabs[3]:
        st.subheader("RFI Desk")
        training_box("RFI",state)
        st.warning("Electrical is waiting: E-201 and A-402 show conflicting outlet mounting heights in Rooms 204–210.")

        st.markdown("#### 📚 Document Control")
        st.caption("This is where you perform Step 1. Verify that the drawings/specifications you are about to reference are current.")
        current_docs=pd.DataFrame([
            ["A-402","Architectural","Interior Elevations / Device Locations","Rev 3","2026-08-18","CURRENT"],
            ["E-201","Electrical","Second Floor Power Plan","Rev 2","2026-08-12","CURRENT"],
            ["A-501","Architectural","Wall Details","Rev 1","2026-07-29","CURRENT"],
            ["E-501","Electrical","Electrical Details","Rev 1","2026-07-30","CURRENT"],
            ["26 27 26","Specification","Wiring Devices","IFC","2026-08-01","CURRENT"]
        ],columns=["Document","Discipline","Title","Revision","Issued","Status"])
        st.dataframe(current_docs,use_container_width=True,hide_index=True)
        with st.expander("🗂️ Superseded revisions — archive"):
            st.dataframe(pd.DataFrame([
                ["A-402","Rev 2","2026-08-02","SUPERSEDED by Rev 3"],
                ["E-201","Rev 1","2026-07-25","SUPERSEDED by Rev 2"]
            ],columns=["Document","Revision","Issued","Status"]),use_container_width=True,hide_index=True)

        checked=st.multiselect(
            "Which current documents did you verify for this conflict?",
            ["A-402 · Rev 3","E-201 · Rev 2","A-501 · Rev 1","E-501 · Rev 1","Spec 26 27 26 · IFC"],
            key="rfi_doc_verify"
        )
        if st.button("✓ Verify Revisions",use_container_width=True,key="rfi_verify_revisions"):
            if {"A-402 · Rev 3","E-201 · Rev 2"}.issubset(set(checked)):
                st.session_state["rfi_revision_verified"]=True
                career_activity(state,"Document Control","RFI documents verified","A-402 Rev 3 and E-201 Rev 2 verified as current.")
                st.success("Step 1 complete: A-402 Rev 3 and E-201 Rev 2 are current.")
            else:
                st.session_state["rfi_revision_verified"]=False
                st.warning("This conflict is between A-402 and E-201. Check the current revision of both documents.")
        if st.session_state.get("rfi_revision_verified"):
            st.success("✓ Current revisions verified. You can now draft the RFI.")
        else:
            st.info("Before drafting: verify both A-402 and E-201 above.")

        with st.form("rfi_form",clear_on_submit=True):
            subject=st.text_input("Subject",placeholder="Receptacle mounting height — Rooms 204–210")
            refs=st.text_input("Drawing / spec references",placeholder="A-402 Interior Elevation 2; E-201 Detail 3",help="Use exact document references.")
            question=st.text_area("Question / requested clarification",height=130,placeholder="State the conflict factually and ask one clear question.")
            impact=st.selectbox("Potential impact",["None known","Schedule","Cost","Schedule + Cost","Field coordination","Other"])
            route=st.form_submit_button("Route RFI",use_container_width=True)
            if route and state["mode"]=="Training" and not st.session_state.get("rfi_revision_verified"):
                st.session_state["rfi_verify_warning"]="Complete Step 1 in Document Control before routing the RFI."
                route=False
            if route:
                num=f"RFI-{17+len(rows('SELECT id FROM career_rfis')):03d}"
                status="Awaiting Response"
                execute("INSERT INTO career_rfis(rfi_no,subject,drawing_ref,question,impact,status,submitted_time) VALUES(?,?,?,?,?,?,?)",(num,subject,refs,question,impact,status,sim_time(state)))
                execute("UPDATE career_tasks SET status='Done',completed_at=? WHERE task_key='T2'",(sim_time(state),))
                execute("UPDATE career_tasks SET status='Done',completed_at=? WHERE task_key LIKE 'CREATE_RFI_%' AND status!='Done'",(sim_time(state),))
                career_activity(state,"RFI",num+" submitted",f"{subject} · {refs} · Status: Awaiting Response")
                advance_sim(state,15)
                # Immediate realistic quality reaction.
                if not refs.strip() or len(question.strip())<35:
                    execute("UPDATE career_rfis SET status='Returned for Revision',response=? WHERE rfi_no=?",("Avery: Please revise this RFI with the applicable drawing/detail references and a clearer description of the conflict.",num))
                    execute("UPDATE career_tasks SET status='In Progress',completed_at=NULL WHERE task_key='T2'")
                    career_activity(state,"RFI Response",num+" returned for revision","Architect needs clearer references/question.")
                    st.session_state["rfi_ok"]=f"⚠️ {num} was routed, but the architect returned it for revision. It is saved in the RFI Log."
                else:
                    execute("UPDATE career_rfis SET response=? WHERE rfi_no=?",('Avery acknowledged receipt. Design response pending.',num))
                    career_activity(state,"RFI Response",num+" acknowledged","Avery Chen confirmed receipt; response pending.")
                    st.session_state["rfi_ok"]=f"✅ {num} SUBMITTED at {sim_time(state)}. It is saved in the RFI Log and Avery acknowledged it."
                    career_queue_message(state,12,"Avery Chen · Architect","Design review — "+num,
                                         'I reviewed the conflict. Use 18" AFF in Rooms 204–210. Please distribute this clarification to the field and update the RFI log.',
                                         "RFI Answer",
                                         task_key=f"DISTRIBUTE_{num}",task_title=f"Distribute {num} response to field",
                                         task_area="RFIs",task_priority="URGENT",task_due_time=_career_time_from_minutes(int(state["minutes"])+25),
                                         task_detail="Send the architect clarification to Dana/Apex and record the response.")
                    career_queue_message(state,20,"Dana Lewis · Superintendent",num+" field follow-up",
                                         "Did design answer yet? I need documented direction before I put electrical back into those rooms.",
                                         "Field Pressure")
                career_reactions(state)
        if st.session_state.get("rfi_ok"): st.success(st.session_state.pop("rfi_ok"))
        if st.session_state.get("rfi_verify_warning"):
            st.warning(st.session_state.pop("rfi_verify_warning"))
        st.markdown("#### RFI Log")
        for r in rows("SELECT * FROM career_rfis ORDER BY id DESC"):
            with st.expander(f"{r['rfi_no']} · {r['subject'] or 'Untitled'} · {r['status']}"):
                st.write("**References:** "+(r["drawing_ref"] or "Missing"))
                st.write("**Question:** "+(r["question"] or ""))
                st.caption(f"Submitted {r['submitted_time']} · Impact: {r['impact']}")
                if r["response"]: st.info(r["response"])
    with tabs[4]:
        st.subheader("Cost Desk · Apex Electric Pay Application")
        training_box("Pay Application",state)
        c=st.columns(4); c[0].metric("Contract","$620,000"); c[1].metric("Previously paid","$310,000"); c[2].metric("Requested","$248,000"); c[3].metric("Field progress","~70%")
        st.warning("Billing requests approximately 90% complete while field reporting indicates about 70% installed.")
        with st.form("cost_review",clear_on_submit=True):
            decision=st.selectbox("Your action",["Hold for verification","Approve as submitted","Return for correction","Ask PM to decide without review"])
            note=st.text_area("Document your review / discrepancy")
            if st.form_submit_button("Submit Cost Review",use_container_width=True):
                advance_sim(state,18)
                if decision in ["Hold for verification","Return for correction"]:
                    msg="Marcus: Good catch. Accounting will hold the affected billing until Apex supports or corrects the percentage."
                    career_activity(state,"Cost Review","Apex Pay App review accepted",msg)
                    execute("UPDATE career_tasks SET status='Done',completed_at=? WHERE task_key='T4'",(sim_time(state),))
                    career_queue_message(state,4,"Jasmine Cole · Accounting","Apex pay app placed on hold",
                                         "Hold is in place. Please send the supported/revised amount before 2:30 PM if the undisputed portion should make today's run.",
                                         "Accounting Reaction",
                                         task_key=f"PAYBACKUP_{state['minutes']}",task_title="Obtain Apex billing backup / correction",
                                         task_area="Cost",task_priority="High",task_due_time="2:30 PM",
                                         task_detail="Get supporting backup or corrected billing and document the approved amount.")
                    career_queue_message(state,11,"Luis Ortega · Apex Electric PM","RE: Pay application hold",
                                         "We disagree with holding the full amount. Material is onsite and rough-in is substantially complete in released areas. I can send invoices and a progress markup.",
                                         "Trade Pushback")
                    st.session_state["cost_ok"]="✅ REVIEW SUBMITTED. "+msg
                else:
                    msg="Marcus returned your review. Field progress does not support the billed percentage; verify before approval."
                    career_activity(state,"Cost Review","Apex Pay App returned for revision",msg)
                    career_queue_message(state,3,"Marcus Reed · Project Manager","Pay app review needs correction",
                                         "Do not approve unsupported billing. Compare the schedule of values to verified field progress and backup, then resubmit your recommendation.",
                                         "PM Correction",
                                         task_key=f"REDOCOST_{state['minutes']}",task_title="Redo Apex pay-app review",
                                         task_area="Cost",task_priority="URGENT",task_due_time="12:30 PM",
                                         task_detail="Verify installed/stored work and submit a supported recommendation.")
                    st.session_state["cost_ok"]="⚠️ REVIEW SUBMITTED, THEN RETURNED. "+msg
                career_reactions(state)
        if st.session_state.get("cost_ok"): st.success(st.session_state.pop("cost_ok"))
    with tabs[5]:
        st.subheader("Project Calendar"); st.write("**8:30 AM** · Framing inspection confirmation deadline"); st.write("**10:00 AM** · OAC Meeting · Owner / Architect / Contractor"); st.write("**12:00 PM** · Pay app internal review"); st.write("**3:00 PM** · Accounting cutoff"); st.write("**Tomorrow 7:00 AM** · Drywall mobilization"); st.write("**Friday** · Metro Interiors COI expiration")
    with tabs[6]:
        st.subheader("Project Team")
        st.dataframe(pd.DataFrame([
            ["Marcus Reed","Project Manager","Cost approval, owner communication, escalation, overall project"],
            ["Dana Lewis","Superintendent","Field operations, sequencing, safety, site verification"],
            ["You","Project Coordinator","Logs, documents, follow-up, routing, cost/admin coordination"],
            ["Avery Chen","Project Architect","Design clarifications, drawing/spec responses, RFIs, submittal review"],
            ["Nia Brooks","Owner Representative","Owner decisions, selections, client approvals"],
            ["Luis Ortega / Apex Electric","Electrical Subcontractor","Electrical manpower/material, trade backup, electrical execution"],
            ["Door Hardware Vendor","Vendor","Hardware package, fabrication, factory slot, lead times"],
            ["Metro Interiors","Subcontractor","Interiors/drywall scope and its compliance documents"],
            ["Inspection Agency","Third-party inspection","Inspection scheduling and confirmation"],
            ["Jasmine Cole / Accounting","Accounting","Payment processing, payment cutoff, administrative backup"]
        ],columns=["Name","Role","Primary lane"]),use_container_width=True,hide_index=True)
        if state["mode"]=="Training":
            st.info("Training tip: choosing the correct recipient is part of the exercise. If you send a clear request to the wrong role, that person may redirect you and explain who should receive it.")
    with tabs[7]:
        st.subheader("📚 Permanent Training Library")
        st.caption("This remains available in Training, Assisted, and Independent modes.")
        topic=st.selectbox("Guide",list(TRAINING_GUIDES.keys()))
        g=TRAINING_GUIDES[topic]
        st.info(g["what"])
        st.markdown("**Step-by-step workflow**")
        for i,x in enumerate(g["steps"],1): st.write(f"{i}. {x}")
        st.markdown("**Completed example**"); st.code(g["example"])
        st.warning("Common mistakes: "+g["mistakes"])
        st.markdown("#### My Project Coordinator Cheat Sheet")
        with st.form("career_note",clear_on_submit=True):
            ntopic=st.selectbox("Topic",list(TRAINING_GUIDES.keys())+["Schedule","General"])
            note=st.text_area("My note / reminder")
            if st.form_submit_button("Save Note"):
                if note.strip(): execute("INSERT INTO career_notes(topic,note,created_at) VALUES(?,?,?)",(ntopic,note,datetime.now().isoformat(timespec="seconds"))); st.rerun()
        for n in rows("SELECT * FROM career_notes ORDER BY id DESC"):
            c=st.columns([1,5,1]); c[0].write("**"+n["topic"]+"**"); c[1].write(n["note"])
            if c[2].button("Delete",key=f"cn{n['id']}"): delete_row("career_notes",n["id"]); st.rerun()
        st.markdown("#### Activity / Submission Log")
        acts=rows("SELECT * FROM career_activity ORDER BY id DESC LIMIT 20")
        for x in acts:
            with st.container(border=True):
                st.markdown(f"**{x['activity_time']} · {x['activity_type']} — {x['title']}**")
                if x["detail"]: st.caption(x["detail"])
    with tabs[8]:
        st.subheader("Scenario Lab · Escalating Pressure"); c=st.columns(3); mode2=c[0].selectbox("Mode",["Learn","Practice","Job"],key="career_mode2"); level=c[1].selectbox("Difficulty",["Beginner","Intermediate","Advanced","Crisis","Any"],key="career_level2"); skill=c[2].selectbox("Skill",["Any"]+sorted(set(x["skill"] for x in SCENARIOS)),key="career_skill2"); pool=[x for x in SCENARIOS if (level=="Any" or x["level"]==level) and (skill=="Any" or x["skill"]==skill)] or SCENARIOS
        if st.button("🎲 Load scenario",use_container_width=True): st.session_state.career_scenario=random.choice(pool)["id"]; st.rerun()
        sid=st.session_state.get("career_scenario",pool[0]["id"]); scn=next((x for x in pool if x["id"]==sid),pool[0]); st.markdown(f"### {scn['title']} · {scn['level']}"); st.write(scn["prompt"]); choices=list(scn["choices"]); random.Random(scn["id"]+str(state["day"])).shuffle(choices); choice=st.radio("Decision",choices,key="choice_"+scn["id"]); other=st.text_area("What else would you do?",key="other_"+scn["id"])
        if st.button("Submit decision",use_container_width=True):
            score=scn["choices"][choice]
            execute("INSERT INTO career_log(log_date,scenario_id,mode,choice,score,skill,note) VALUES(?,?,?,?,?,?,?)",(date.today().isoformat(),scn["id"],mode2,choice,score,scn["skill"],other))
            career_activity(state,"Scenario Decision",scn["title"],f"Decision: {choice} · Score {score}")
            if score>=9:
                career_queue_message(state,8,"Marcus Reed · Project Manager","RE: "+scn["title"],
                                     "Good call. That protects the project and gives the team a documented next step. Keep the follow-up moving.",
                                     "Positive Feedback")
            elif score>=4:
                career_queue_message(state,6,"Marcus Reed · Project Manager","Follow-up — "+scn["title"],
                                     "Your response is workable, but there is still exposure. Tighten the documentation, ownership, and follow-up time before this drifts.",
                                     "Coaching")
            else:
                career_queue_message(state,4,"Marcus Reed · Project Manager","Escalation — "+scn["title"],
                                     "This created project risk. Stop and correct the action before the issue affects cost, schedule, or the field.",
                                     "Escalation",
                                     task_key=f"CORRECT_{scn['id']}_{state['minutes']}",task_title="Correct scenario decision: "+scn["title"],
                                     task_area=scn["skill"],task_priority="URGENT",task_due_time=_career_time_from_minutes(int(state["minutes"])+25),
                                     task_detail="Review the experienced coordinator response and take a corrective project-control action.")
            advance_sim(state,8)
            st.session_state["result_"+scn["id"]]=score
        if "result_"+scn["id"] in st.session_state:
            score=st.session_state["result_"+scn["id"]]; st.success("Strong coordinator decision.") if score>=9 else st.warning("There is a stronger project-control response.") if score>=4 else st.error("This creates significant project risk."); st.write("**Experienced coordinator response:** "+scn["best"]); st.write(scn["why"])
    with tabs[9]:
        st.subheader("Performance Review"); done=rows("SELECT COUNT(*) n FROM career_tasks WHERE status='Done'")[0]["n"]; total=rows("SELECT COUNT(*) n FROM career_tasks")[0]["n"]; log=df_from("SELECT * FROM career_log ORDER BY id DESC"); c=st.columns(4); c[0].metric("Work queue",f"{done}/{total}"); c[1].metric("Scenarios",len(log)); c[2].metric("Decision score",f"{log.score.mean():.1f}/10" if not log.empty else "—"); c[3].metric("Sim time",sim_time(state));
        if not log.empty: st.bar_chart(log.groupby("skill").score.mean())
        st.info("Performance grows across documentation, prioritization, communication, cost awareness, schedule awareness and follow-through.")
        with st.expander("🗑️ Reset simulated project"):
            confirm=st.checkbox("I understand this restarts the construction simulation")
            if st.button("Reset Career Simulator",disabled=not confirm):
                for tbl in ["career_tasks","career_messages","career_log","career_sent","career_activity","career_rfis","career_notes","career_reaction_queue"]: reset_table(tbl)
                execute("DELETE FROM settings WHERE key='career_workday'"); st.rerun()


# ---------- Health & Life ----------
def health_summary():
    today=date.today().isoformat()
    h=rows("SELECT * FROM health_daily WHERE log_date=?",(today,))
    meds=rows("SELECT * FROM medicines WHERE active=1")
    taken=rows("SELECT * FROM medicine_doses WHERE dose_date=? AND status='Taken'",(today,))
    cycle=rows("SELECT * FROM cycle_logs ORDER BY log_date DESC,id DESC LIMIT 1")
    return (h[0] if h else None),len(meds),len(taken),(cycle[0] if cycle else None)

def health():
    st.title("❤️ Health & Life")
    st.caption("Activity, cycle, medicines/supplements, vitamins, and schedule-aware planning in one place.")
    tabs=st.tabs(["Today","📱 Samsung Health","🩸 Cycle","💊 Medicines & Supplements","🧪 Nutrients","📅 Calendar Planning","📈 Health Progress"])

    with tabs[0]:
        h,med_count,taken_count,cy=health_summary()
        c=st.columns(4)
        c[0].metric("Steps",f"{int(h['steps'] or 0):,}" if h else "—")
        c[1].metric("Active calories",f"{int(h['active_calories'] or 0):,}" if h else "—")
        c[2].metric("Heart rate",f"{int(h['avg_hr'] or 0)} bpm" if h and h['avg_hr'] else "—")
        c[3].metric("Meds/supplements",f"{taken_count}/{med_count} logged")
        if cy: st.caption(f"Latest cycle log: {cy['period_status']} • Energy: {cy['energy']} • {cy['log_date']}")
        st.markdown("#### Quick health log")
        with st.form("quickhealth"):
            c=st.columns(4)
            steps=c[0].number_input("Steps",min_value=0,step=100)
            active=c[1].number_input("Active calories",min_value=0.0,step=10.0)
            total=c[2].number_input("Total calories burned",min_value=0.0,step=10.0)
            hr=c[3].number_input("Average heart rate",min_value=0.0,step=1.0)
            c=st.columns(4)
            resting=c[0].number_input("Resting HR",min_value=0.0,step=1.0)
            mins=c[1].number_input("Active minutes",min_value=0.0,step=5.0)
            sleep=c[2].number_input("Sleep hours",min_value=0.0,max_value=24.0,step=.25)
            note=c[3].text_input("Note")
            if st.form_submit_button("Save Today's Health",use_container_width=True):
                execute("""INSERT INTO health_daily(log_date,steps,active_calories,total_calories,avg_hr,resting_hr,active_minutes,sleep_hours,source,note)
                           VALUES(?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(log_date) DO UPDATE SET steps=excluded.steps,active_calories=excluded.active_calories,total_calories=excluded.total_calories,avg_hr=excluded.avg_hr,resting_hr=excluded.resting_hr,active_minutes=excluded.active_minutes,sleep_hours=excluded.sleep_hours,source=excluded.source,note=excluded.note""",
                        (date.today().isoformat(),steps,active,total,hr,resting,mins,sleep,"Manual",note)); st.rerun()

    with tabs[1]:
        st.subheader("📱 Import Samsung Health Screenshot")
        st.info("Upload a screenshot, then confirm the numbers before saving. ChapLife keeps active calories and total calories separate.")
        up=st.file_uploader("Samsung Health screenshot",type=["png","jpg","jpeg"],key="samsung_health")
        if up:
            st.image(up,use_container_width=True)
            st.caption("Screenshot loaded. Enter/confirm the values visible in the screenshot. The confirmation step prevents a misread image from becoming permanent health data.")
            with st.form("confirm_samsung"):
                d=st.date_input("Date shown",date.today())
                c=st.columns(4)
                steps=c[0].number_input("Steps shown",min_value=0,step=100,key="shsteps")
                active=c[1].number_input("Active calories shown",min_value=0.0,step=10.0,key="shactive")
                total=c[2].number_input("Total calories shown",min_value=0.0,step=10.0,key="shtotal")
                hr=c[3].number_input("Heart rate / average shown",min_value=0.0,step=1.0,key="shhr")
                c=st.columns(3)
                resting=c[0].number_input("Resting HR if shown",min_value=0.0,step=1.0,key="shrest")
                mins=c[1].number_input("Activity minutes if shown",min_value=0.0,step=5.0,key="shmins")
                sleep=c[2].number_input("Sleep hours if shown",min_value=0.0,max_value=24.0,step=.25,key="shsleep")
                if st.form_submit_button("✓ Confirm & Save Screenshot Data",use_container_width=True):
                    execute("""INSERT INTO health_daily(log_date,steps,active_calories,total_calories,avg_hr,resting_hr,active_minutes,sleep_hours,source,note)
                               VALUES(?,?,?,?,?,?,?,?,?,?)
                               ON CONFLICT(log_date) DO UPDATE SET steps=excluded.steps,active_calories=excluded.active_calories,total_calories=excluded.total_calories,avg_hr=excluded.avg_hr,resting_hr=excluded.resting_hr,active_minutes=excluded.active_minutes,sleep_hours=excluded.sleep_hours,source=excluded.source""",
                            (d.isoformat(),steps,active,total,hr,resting,mins,sleep,"Samsung Health Screenshot","Confirmed from screenshot"))
                    execute("INSERT INTO health_imports(import_date,import_type,filename,extracted_text,confirmed) VALUES(?,?,?,?,1)",(date.today().isoformat(),"Samsung Health",up.name,"User-confirmed screenshot values"))
                    st.success("✓ Samsung Health data saved."); st.rerun()

    with tabs[2]:
        st.subheader("🩸 Cycle Tracker")
        with st.form("cyclelog",clear_on_submit=True):
            c=st.columns(4)
            d=c[0].date_input("Date",date.today(),key="cycledate")
            status=c[1].selectbox("Period status",["No period","Started today","Period day","Ended today","Spotting"])
            flow=c[2].selectbox("Flow",["None","Light","Medium","Heavy"])
            cramps=c[3].selectbox("Cramps",["None","Mild","Moderate","Strong"])
            c=st.columns(4)
            mood=c[0].selectbox("Mood",["Good","Calm","Irritable","Emotional","Anxious","Low","Other"])
            energy=c[1].selectbox("Energy",["High","Normal","Low","Very low"])
            symptoms=c[2].multiselect("Symptoms",["Bloating","Cravings","Headache","Backache","Breast tenderness","Acne","Nausea","Fatigue","Other"])
            note=c[3].text_input("Other / notes")
            if st.form_submit_button("Save Cycle Log",use_container_width=True):
                execute("INSERT INTO cycle_logs(log_date,period_status,flow,cramps,mood,energy,symptoms,note) VALUES(?,?,?,?,?,?,?,?)",(d.isoformat(),status,flow,cramps,mood,energy,", ".join(symptoms),note)); st.rerun()
        logs=df_from("SELECT * FROM cycle_logs ORDER BY log_date DESC,id DESC")
        if not logs.empty: st.dataframe(logs,use_container_width=True,hide_index=True)
        st.caption("Cycle timing shown by ChapLife is an estimate based on what you log, not a medical prediction.")
        delete_reset_panel("cycle_logs","cycle logs","log_date")

    with tabs[3]:
        st.subheader("💊 Medicines & Supplements")
        st.caption("Prescription • OTC • Vitamin • Supplement • Other")
        st.markdown("#### 📸 Scan Bottle / Label")
        medphoto=st.file_uploader("Upload front/back bottle, box, Drug Facts, or Supplement Facts photo",type=["png","jpg","jpeg"],accept_multiple_files=True,key="medphoto")
        if medphoto:
            for f in medphoto: st.image(f,caption=f.name,width=300)
            st.info("Photos loaded. Review and confirm the label information below before saving. Avoid storing unnecessary pharmacy identifiers such as prescription numbers.")
        with st.form("addmedicine",clear_on_submit=True):
            c=st.columns(4)
            name=c[0].text_input("Product / medicine name")
            brand=c[1].text_input("Brand")
            typ=c[2].selectbox("Type",["Prescription","OTC Medicine","Vitamin","Supplement","Other"])
            strength=c[3].text_input("Strength",placeholder="500 mg, 25 mcg, etc.")
            c=st.columns(4)
            serving=c[0].text_input("Serving / dose",placeholder="2 capsules")
            directions=c[1].text_input("Label directions",placeholder="Take 2 daily")
            food=c[2].selectbox("With food?",["Not specified","Yes","No","Either"])
            reason=c[3].text_input("Why I take it / goal")
            c=st.columns(3)
            startd=c[0].date_input("Start date",date.today())
            endtxt=c[1].text_input("End date if applicable")
            labelnotes=c[2].text_input("Label notes / warnings")
            if st.form_submit_button("Confirm & Save Product",use_container_width=True):
                mid=execute("INSERT INTO medicines(name,brand,med_type,strength,serving,directions,reason,start_date,end_date,with_food,active,label_notes) VALUES(?,?,?,?,?,?,?,?,?,?,1,?)",
                            (name,brand,typ,strength,serving,directions,reason,startd.isoformat(),endtxt,food,labelnotes))
                st.session_state["last_med_id"]=mid; st.success("✓ Product saved. Add its vitamins/minerals in the Nutrients tab."); st.rerun()
        meds=rows("SELECT * FROM medicines WHERE active=1 ORDER BY id DESC")
        for m in meds:
            with st.container(border=True):
                c=st.columns([3,1,1])
                c[0].markdown(f"**{m['brand']+' ' if m['brand'] else ''}{m['name']}**  \n{m['med_type']} • {m['strength'] or 'strength not entered'} • {m['directions'] or 'directions not entered'}")
                if c[1].button("✓ Taken Today",key=f"taken{m['id']}"):
                    execute("INSERT INTO medicine_doses(medicine_id,dose_date,dose_time,status,note) VALUES(?,?,?,?,?)",(m["id"],date.today().isoformat(),datetime.now().strftime("%H:%M"),"Taken","")); st.rerun()
                if c[2].button("Deactivate",key=f"deact{m['id']}"):
                    execute("UPDATE medicines SET active=0 WHERE id=?",(m["id"],)); st.rerun()
                st.caption("Would I benefit from this? ChapLife can organize the ingredients, your stated goal, and overlaps; medication/supplement changes should not be made from this tracker alone.")

    with tabs[4]:
        st.subheader("🧪 Vitamin & Nutrient Information")
        meds=rows("SELECT * FROM medicines WHERE active=1 ORDER BY name")
        if meds:
            opts={f"{m['brand']+' ' if m['brand'] else ''}{m['name']}":m["id"] for m in meds}
            pick=st.selectbox("Product",list(opts))
            mid=opts[pick]
            with st.form("addnutrient",clear_on_submit=True):
                c=st.columns(4)
                nutrient=c[0].text_input("Vitamin / mineral / nutrient",placeholder="Vitamin D")
                amount=c[1].number_input("Amount per serving",min_value=0.0,step=.1)
                unit=c[2].selectbox("Unit",["mg","mcg","g","IU","CFU","Other"])
                dv=c[3].text_input("% Daily Value if shown")
                source=st.text_input("Label wording / ingredient note")
                if st.form_submit_button("Add Label Nutrient"):
                    execute("INSERT INTO medicine_nutrients(medicine_id,nutrient,amount,unit,daily_value,source_text) VALUES(?,?,?,?,?,?)",(mid,nutrient,amount,unit,dv,source)); st.rerun()
        totals=rows("""SELECT n.nutrient,n.unit,SUM(n.amount) total,COUNT(DISTINCT n.medicine_id) products
                       FROM medicine_nutrients n JOIN medicines m ON m.id=n.medicine_id
                       WHERE m.active=1 GROUP BY n.nutrient,n.unit ORDER BY n.nutrient""")
        if totals:
            st.markdown("#### Known supplement totals per labeled serving")
            for x in totals:
                flag=" ⚠️ from multiple products" if x["products"]>1 else ""
                st.write(f"**{x['nutrient']}:** {x['total']:g} {x['unit']}{flag}")
            st.caption("These totals reflect only label amounts you saved. Food micronutrients should remain separately identified unless reliable amounts are available.")
        else: st.info("Add label nutrients from your medicines/supplements to see overlaps here.")

    with tabs[5]:
        st.subheader("📅 Calendar-Aware Planning")
        st.success("Google Calendar connection is available for ChapLife planning.")
        st.write("Calendar events can influence **meal difficulty, meal timing, workout length, workout timing, and whether a meal may need to be away from home**.")
        st.markdown("**Planning controls for imported events**")
        st.write("• Use for Planning ✓  • Ignore This Event  • Treat as Busy  • Add Travel Time  • Meal Needed Away From Home")
        st.info("Busy day → simpler meal + shorter workout. Lighter day → longer workout or meal-prep opportunity. You stay in control of the adjustment.")
        events=df_from("SELECT * FROM calendar_planning ORDER BY event_date,start_time")
        if not events.empty: st.dataframe(events,use_container_width=True,hide_index=True)
        st.caption("The downloaded local app contains the planning interface. Live Google Calendar syncing requires the hosted/connected version rather than embedding your account credentials in the ZIP.")

    with tabs[6]:
        st.subheader("📈 Health Progress")
        h=df_from("SELECT * FROM health_daily ORDER BY log_date DESC")
        if h.empty: st.info("Save health data for a few days to begin seeing trends.")
        else:
            st.dataframe(h,use_container_width=True,hide_index=True)
            recent=h.head(7)
            c=st.columns(4)
            c[0].metric("7-day avg steps",f"{recent.steps.fillna(0).mean():,.0f}")
            c[1].metric("Avg active calories",f"{recent.active_calories.fillna(0).mean():,.0f}")
            c[2].metric("Avg active minutes",f"{recent.active_minutes.fillna(0).mean():.0f}")
            c[3].metric("Avg sleep",f"{recent.sleep_hours.fillna(0).mean():.1f} hr")
        st.markdown("#### Dashboard-style insight")
        if len(h)>=3:
            st.success("✅ Good: You're building a health history ChapLife can use for planning.")
            st.success("✅ Good: Activity data is being separated into useful measures instead of one generic score.")
            st.warning("🔧 Improvement: Keep logging consistently so meal/workout recommendations can respond to actual patterns.")
        else:
            st.info("Complete at least 3 daily health logs for your first 2-good-things + 1-improvement summary.")


# ---------- Settings ----------
def settings_page():
    st.title('⚙️ Settings')
    st.caption('Control what ChapLife shows, how planning works, and future account integrations.')

    tabs=st.tabs(['Display & Progress','📅 Calendar','🥗 Meal Planning','🏋🏾‍♀️ Workout Planning','❤️ Health','Data & Privacy'])

    with tabs[0]:
        st.subheader('My Progress sections')
        st.write('Hide sections you do not want to see in **My Progress**. Your saved information is not deleted.')
        show_growth=st.toggle('Show Growth in My Progress',value=bool(get_setting('progress_show_growth',True)),key='set_progress_growth')
        show_convo=st.toggle('Show Conversation in My Progress',value=bool(get_setting('progress_show_conversation',True)),key='set_progress_convo')
        if show_growth!=bool(get_setting('progress_show_growth',True)):
            set_setting('progress_show_growth',show_growth); st.rerun()
        if show_convo!=bool(get_setting('progress_show_conversation',True)):
            set_setting('progress_show_conversation',show_convo); st.rerun()

        st.divider()
        st.subheader('Dashboard visibility')
        st.caption('These controls can later be expanded so you can hide whole dashboard cards too.')
        st.info('Growth Lab and Conversation remain available from the main navigation even when hidden from My Progress.')

    with tabs[1]:
        st.subheader('📅 Google Calendar')
        st.warning('Calendar is not connected directly to this hosted ChapLife app yet.')
        st.write('Your Google Calendar connection in ChatGPT is separate from ChapLife. ChapLife needs its **own secure Google sign-in/OAuth connection** before it can read your schedule automatically.')
        st.markdown('**Once connected, ChapLife will be allowed to use calendar events for:**')
        use_meals=st.toggle('Adjust meal plans around busy days',value=bool(get_setting('calendar_meal_planning',True)),key='calmeal')
        use_workouts=st.toggle('Adjust workout length/timing around events',value=bool(get_setting('calendar_workout_planning',True)),key='calwork')
        away=st.toggle('Flag days when I may need a meal away from home',value=bool(get_setting('calendar_away_meals',True)),key='calaway')
        travel=st.number_input('Default travel buffer around events (minutes)',min_value=0,max_value=180,step=5,value=int(get_setting('calendar_travel_buffer',30) or 30))
        if st.button('Save Calendar Planning Preferences',use_container_width=True):
            set_setting('calendar_meal_planning',use_meals)
            set_setting('calendar_workout_planning',use_workouts)
            set_setting('calendar_away_meals',away)
            set_setting('calendar_travel_buffer',travel)
            st.success('Calendar planning preferences saved.')
        st.info('Next cloud step: add a **Connect Google Calendar** button here using Google OAuth. No Google password will be stored in ChapLife.')

    with tabs[2]:
        st.subheader('🥗 Meal planning preferences')
        meals_per_day=st.selectbox('Typical meals per day',[2,3,4,5],index=max(0,min(3,int(get_setting('meal_count',3) or 3)-2)))
        cook_time=st.selectbox('Typical cooking time',['10–15 minutes','20–30 minutes','30–45 minutes','I am flexible'],index=0)
        leftovers=st.toggle('Use leftovers to reduce waste',value=bool(get_setting('meal_use_leftovers',True)))
        if st.button('Save Meal Preferences',use_container_width=True):
            set_setting('meal_count',meals_per_day); set_setting('meal_cook_time',cook_time); set_setting('meal_use_leftovers',leftovers)
            st.success('Meal preferences saved.')

    with tabs[3]:
        st.subheader('🏋🏾‍♀️ Workout planning preferences')
        busy_length=st.selectbox('Workout length on busy days',['10 minutes','15 minutes','20 minutes','30 minutes'],index=2)
        normal_length=st.selectbox('Workout length on normal days',['20 minutes','30 minutes','40 minutes','45 minutes','60 minutes'],index=2)
        calendar_adjust=st.toggle('Let calendar busyness shorten a workout suggestion',value=bool(get_setting('workout_calendar_adjust',True)))
        if st.button('Save Workout Preferences',use_container_width=True):
            set_setting('workout_busy_length',busy_length); set_setting('workout_normal_length',normal_length); set_setting('workout_calendar_adjust',calendar_adjust)
            st.success('Workout preferences saved.')

    with tabs[4]:
        st.subheader('❤️ Health preferences')
        st.write('Control how health information is used in planning.')
        cycle_adjust=st.toggle('Allow logged energy/cycle information to suggest lighter workout options',value=bool(get_setting('health_cycle_adjust',True)))
        samsung=st.toggle('Use Samsung Health activity history in progress summaries',value=bool(get_setting('health_use_samsung',True)))
        nutrients=st.toggle('Include supplement-label nutrients in nutrient summaries',value=bool(get_setting('health_use_supplement_nutrients',True)))
        if st.button('Save Health Preferences',use_container_width=True):
            set_setting('health_cycle_adjust',cycle_adjust); set_setting('health_use_samsung',samsung); set_setting('health_use_supplement_nutrients',nutrients)
            st.success('Health preferences saved.')

    with tabs[5]:
        st.subheader('Data & privacy')
        st.write('ChapLife is currently hosted from GitHub, but personal data should live in a private cloud database—not in the public repository.')
        st.warning('Do not upload `chaplife.db`, financial exports, health screenshots, medicine-label photos, passwords, or API credentials to the public GitHub repository.')
        st.info('The next sync step will move saved records to private cloud storage so phone and computer use the same data.')

# ---------- Progress ----------
def progress():
    st.title('📈 My Progress')
    show_growth=bool(get_setting('progress_show_growth',True))
    show_convo=bool(get_setting('progress_show_conversation',True))

    tab_names=['Overview','Money','Nutrition','Fitness & Water']
    if show_growth: tab_names.append('Growth')
    if show_convo: tab_names.append('Conversation')
    tab_names.extend(['Career','Health'])
    ptab=st.tabs(tab_names)
    tabs=dict(zip(tab_names,ptab))

    start=(date.today()-timedelta(days=30)).isoformat()
    workouts=df_from('SELECT * FROM workouts WHERE workout_date>=?',(start,))
    meals=df_from('SELECT * FROM meals WHERE meal_date>=?',(start,))
    careerlog=df_from('SELECT * FROM career_log WHERE log_date>=?',(start,))
    growthlog=df_from('SELECT * FROM growth_log WHERE log_date>=?',(start,))
    goals=df_from('SELECT * FROM savings_goals')
    water30=df_from('SELECT log_date,SUM(ounces) ounces FROM water_log WHERE log_date>=? GROUP BY log_date',(start,))
    tx=df_from('SELECT * FROM finance_transactions WHERE tx_date>=?',(start,))

    with tabs['Overview']:
        c=st.columns(5)
        c[0].metric('Workouts / 30d',len(workouts))
        c[1].metric('Meals logged / 30d',len(meals))
        c[2].metric('Savings progress',money(goals.current_amount.sum() if not goals.empty else 0))
        c[3].metric('Career scenarios',len(careerlog))
        c[4].metric('Jug levels passed',len(get_setting('jug_passed',[]) or []))
        st.caption('Use ⚙️ Settings to hide Growth or Conversation from My Progress without deleting their data.')

    with tabs['Money']:
        st.subheader('💰 Money Progress')
        if tx.empty:
            st.info('Log transactions to see detailed money progress.')
        else:
            expenses=tx[tx.tx_type=='Expense'] if 'tx_type' in tx.columns else tx.iloc[0:0]
            income=tx[tx.tx_type=='Income'] if 'tx_type' in tx.columns else tx.iloc[0:0]
            c=st.columns(3)
            c[0].metric('Income / 30d',money(income.amount.sum() if not income.empty else 0))
            c[1].metric('Expenses / 30d',money(expenses.amount.sum() if not expenses.empty else 0))
            c[2].metric('Net logged',money((income.amount.sum() if not income.empty else 0)-(expenses.amount.sum() if not expenses.empty else 0)))
            if not expenses.empty and 'category' in expenses.columns:
                st.bar_chart(expenses.groupby('category').amount.sum())
        if not goals.empty:
            st.markdown('#### Savings goals')
            for _,g in goals.iterrows():
                st.write(f"**{g['name']}** — {money(g.current_amount)} / {money(g.target_amount)}")
                st.progress(min(1,g.current_amount/g.target_amount if g.target_amount else 0))

    with tabs['Nutrition']:
        st.subheader('🥗 Nutrition Progress')
        if meals.empty: st.info('Log/check off meals to see detailed nutrition progress.')
        else:
            daily=meals.groupby('meal_date')[['calories','protein']].sum()
            st.line_chart(daily)
            c=st.columns(3)
            c[0].metric('Meals logged',len(meals))
            c[1].metric('Avg calories logged/day',f"{daily.calories.mean():.0f}")
            c[2].metric('Avg protein logged/day',f"{daily.protein.mean():.0f} g")

    with tabs['Fitness & Water']:
        st.subheader('🏋🏾‍♀️ Fitness & 💧 Water')
        if not workouts.empty:
            st.markdown('#### Workout minutes')
            st.bar_chart(workouts.groupby('workout_date').minutes.sum())
        else: st.info('Complete workouts to see fitness trends.')
        if not water30.empty:
            st.markdown('#### Water')
            st.line_chart(water30.set_index('log_date'))
        passed=get_setting('jug_passed',[]) or []
        st.metric('Jug puzzle levels passed',len(passed),f'Highest unlocked: {get_setting("jug_unlocked",1)}')

    if show_growth:
        with tabs['Growth']:
            st.subheader('🌱 Growth Progress')
            if growthlog.empty: st.info('Complete Growth Lab exercises to see detailed progress.')
            else:
                st.metric('Growth entries / 30d',len(growthlog))
                st.dataframe(growthlog,use_container_width=True,hide_index=True)

    if show_convo:
        with tabs['Conversation']:
            st.subheader('💬 Conversation Progress')
            convo=df_from('SELECT * FROM confidence_log WHERE log_date>=? ORDER BY log_date DESC',(start,))
            if convo.empty:
                st.info('Complete conversation practice to begin detailed conversation progress.')
            else:
                st.metric('Conversation practice entries / 30d',len(convo))
                st.dataframe(convo,use_container_width=True,hide_index=True)
            st.caption('Future summaries will include follow-up questions, repeated phrases, contribution of your own thoughts, networking, romance, and group-conversation skills.')

    with tabs['Career']:
        st.subheader('🏗️ Career Progress')
        acts=df_from('SELECT * FROM career_activity ORDER BY id DESC')
        rfis=df_from('SELECT * FROM career_rfis ORDER BY id DESC')
        c=st.columns(3)
        c[0].metric('Career log entries',len(careerlog))
        c[1].metric('Project activities',len(acts))
        c[2].metric('RFIs created',len(rfis))
        if not acts.empty: st.dataframe(acts.head(20),use_container_width=True,hide_index=True)

    with tabs['Health']:
        st.subheader('❤️ Health Detail')
        hd=df_from('SELECT * FROM health_daily WHERE log_date>=? ORDER BY log_date',(start,))
        doses=df_from('SELECT * FROM medicine_doses WHERE dose_date>=? ORDER BY dose_date',(start,))
        cycles=df_from('SELECT * FROM cycle_logs WHERE log_date>=? ORDER BY log_date',(start,))
        if hd.empty: st.info('No health history yet.')
        else:
            c=st.columns(4)
            c[0].metric('Avg steps',f"{hd.steps.fillna(0).mean():,.0f}")
            c[1].metric('Avg active calories',f"{hd.active_calories.fillna(0).mean():,.0f}")
            c[2].metric('Avg active minutes',f"{hd.active_minutes.fillna(0).mean():.0f}")
            c[3].metric('Avg sleep',f"{hd.sleep_hours.fillna(0).mean():.1f} hr")
            if {'steps','active_calories'}.issubset(hd.columns):
                st.line_chart(hd.set_index('log_date')[['steps','active_calories']])
        st.write(f"**Medicine/supplement doses logged:** {len(doses)}")
        st.write(f"**Cycle entries logged:** {len(cycles)}")

# ---------- Render ----------
page=st.session_state.page
if page=='Home': home()
elif page=='Finances': finances()
elif page=='Food & Nutrition': food()
elif page=='Grocery Shopping': grocery()
elif page=='My Trainer': trainer()
elif page=='Water & Jug Puzzles': water_page()
elif page=='Vocabulary': vocabulary()
elif page=='Growth Lab': growth()
elif page=='Conversation & Current Events': current_events()
elif page=='Health & Life': health()
elif page=='Career Simulator': career()
elif page=='My Progress': progress()
elif page=='Settings': settings_page()
