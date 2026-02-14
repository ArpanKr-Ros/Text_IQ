from fastapi import FastAPI,Form
from datetime import timezone,datetime
import sqlite3
from pydantic import BaseModel
from llm_gem import autocorrect, summarise
from fastapi.middleware.cors import CORSMiddleware
from local_llm import llm_autocorrect_and_summarize





app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],  # allow OPTIONS, POST, GET
    allow_headers=["*"],
)

DB_NAME = r"C:\Users\LENOVO\Downloads\sqlite-tools-win-x64-3510200\newdb.db"

def GET_DB():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn



class MessageIn(BaseModel):
    request: str=Form(...)
    task:str=Form(...)


@app.post('/messages')
def rq(msg: MessageIn):

    print("---- NEW REQUEST RECEIVED ----")
    print("Task:", msg.task)
    print("Request:", msg.request)
    
    local_result = llm_autocorrect_and_summarize(msg.request, msg.task)

    use_cloud = True

    if "confidence" in local_result:
      if local_result['confidence']>70:
       model='local'
       confidence = local_result["confidence"]
       response_text= local_result['output']
       use_cloud = False
       print("✅ Using LOCAL LLM")
      else:
        print("⚠️ Local confidence low:", local_result["confidence"])
    

    
    if use_cloud:
        print("☁️ Falling back to GEMINI")
        confidence = None
        model='gemini'
        if msg.task.lower() == "autocorrect":
            response_text = autocorrect(msg.request)
        elif msg.task.lower() == "summarise":
            response_text = summarise(msg.request)
        

    print(" Default flow (DB + hello response)")

    conn = GET_DB()
    now = datetime.now(timezone.utc).isoformat()
    
   # response_text = 'hello ' + msg.request

    print("Saving to DB:")
    print("  request =", msg.request)
    print("  created_at =", now)
    print("  response =", response_text)

    conn.execute(
        'INSERT INTO messages(request, created_at, response,model,confidence) VALUES (?, ?, ?,?,?)',
        (msg.request, now, response_text,model,confidence)
    )
    conn.commit()
    conn.close()

    print("DB commit done")
    print("Sending response back to client")
    print("-----------------------------")

    return {
        'request': msg.request,
        'created_at': now,
        'response': response_text,
        'model_used':model,
        'confidence':confidence
    }

@app.get('/messages')
def get_message():
    conn=GET_DB()
    msg=conn.execute("SELECT * FROM messages").fetchall()
    conn.close()
    return [dict(row) for row in msg]

@app.delete('/messages/{user_id}')
def delete_users(user_id:int):
       conn=GET_DB()
       cur=conn.cursor()
       cur.execute('DELETE FROM messages WHERE id=?',
       (user_id,))
       conn.commit()
       row_count= cur.rowcount
       conn.close()

       if row_count==0:
              return{'error':'user not found'}
       return{'success':'user deleted'}


    