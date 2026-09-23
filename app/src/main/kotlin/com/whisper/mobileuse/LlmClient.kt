package com.whisper.mobileuse
import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
data class PlanResult(val message:String,val actions:List<Action>)
object LlmClient{
 fun plan(context:Context,task:String,ui:String):PlanResult{val p=context.getSharedPreferences("mobile_use",0);val endpoint=p.getString("endpoint","")!!.trim();val key=p.getString("key","")!!;if(endpoint.isBlank()||key.isBlank())return PlanResult("Set an LLM endpoint and API key first.",emptyList())
 return try{val system="You control an Android phone through AccessibilityService. Return ONLY JSON with keys message and actions. Actions: tap{text}, type{text}, back, home, scroll{direction}, wait{x}. Prefer visible labels. Never invent UI state. Task: "+task+" Current UI: "+ui
 val body=JSONObject().put("model","gpt-4o-mini").put("messages",JSONArray().put(JSONObject().put("role","system").put("content",system)).put(JSONObject().put("role","user").put("content",task))).put("temperature",0).toString()
 val c=URL(endpoint).openConnection() as HttpURLConnection;c.requestMethod="POST";c.doOutput=true;c.connectTimeout=15000;c.readTimeout=60000;c.setRequestProperty("Content-Type","application/json");c.setRequestProperty("Authorization","Bearer "+key);c.outputStream.use{it.write(body.toByteArray())};val raw=c.inputStream.bufferedReader().readText();c.disconnect()
 val content=JSONObject(raw).getJSONArray("choices").getJSONObject(0).getJSONObject("message").getString("content");val o=JSONObject(content.trim());val a=o.optJSONArray("actions")?:JSONArray();val list=mutableListOf<Action>();for(i in 0 until a.length()){val x=a.getJSONObject(i);list+=Action(x.optString("type"),x.optString("text"),x.optDouble("x",0.0).toFloat(),x.optDouble("y",0.0).toFloat(),x.optString("direction"))};PlanResult(o.optString("message","Done"),list)
 }catch(e:Exception){PlanResult("Error: "+e.toString(),emptyList())}}
}