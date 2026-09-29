import os
from flask import Flask,jsonify,render_template,request
from dotenv import load_dotenv
from google import genai
from google.genai import types
from chatbot_config import MODEL_NAME,SYSTEM_PROMPT
load_dotenv()
app=Flask(__name__)
key=os.getenv("GEMINI_API_KEY")
if not key: raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
client=genai.Client(api_key=key)
@app.get("/")
def index(): return render_template("index.html")
@app.post("/api/chat")
def chat():
    data=request.get_json(silent=True) or {}; msg=str(data.get("message","")).strip()
    hist=data.get("history",[])
    if not msg: return jsonify({"error":"Please enter a question."}),400
    lines=[]
    for x in hist[-10:] if isinstance(hist,list) else []:
        if isinstance(x,dict) and x.get("content"): lines.append(("Student" if x.get("role")=="user" else "Tutor")+": "+str(x["content"]))
    prompt="\n".join(lines)+("\n" if lines else "")+"Student: "+msg+"\nTutor:"
    try:
        r=client.models.generate_content(model=MODEL_NAME,contents=prompt,config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,tools=[types.Tool(google_search=types.GoogleSearch())],temperature=1.0))
        sources=[]
        gm=getattr(r,"grounding_metadata",None)
        for c in (getattr(gm,"grounding_chunks",None) or []):
            w=getattr(c,"web",None)
            if w and getattr(w,"uri",None): sources.append({"title":getattr(w,"title","Source"),"url":w.uri})
        seen=set(); sources=[s for s in sources if not (s["url"] in seen or seen.add(s["url"]))]
        return jsonify({"answer":(r.text or "").strip(),"sources":sources[:6]})
    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({"error":"The AI service could not process the request right now."}),502
if __name__=="__main__": app.run()
