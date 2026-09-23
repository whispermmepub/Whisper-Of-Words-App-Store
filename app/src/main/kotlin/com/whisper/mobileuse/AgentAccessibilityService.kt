package com.whisper.mobileuse
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.concurrent.Executors
data class Action(val type:String,val text:String="",val x:Float=0f,val y:Float=0f,val direction:String="")
class AgentAccessibilityService:AccessibilityService(){
 companion object{var instance:AgentAccessibilityService?=null};private val executor=Executors.newSingleThreadExecutor()
 override fun onServiceConnected(){super.onServiceConnected();instance=this};override fun onAccessibilityEvent(e:AccessibilityEvent?){};override fun onInterrupt(){};override fun onDestroy(){if(instance===this)instance=null;super.onDestroy()}
 fun snapshot():String{val root=rootInActiveWindow?:return"No active window.";val out=StringBuilder();fun walk(n:AccessibilityNodeInfo,d:Int){if(d>8)return;val t=n.text?.toString()?.replace("\n"," ")?.take(120);val q=n.contentDescription?.toString()?.replace("\n"," ")?.take(120);if(!t.isNullOrBlank()||!q.isNullOrBlank())out.append("  ".repeat(d)).append("class=").append(n.className).append(" text=").append(t).append(" desc=").append(q).append(" clickable=").append(n.isClickable).append("\n");for(i in 0 until n.childCount)n.getChild(i)?.let{walk(it,d+1)}};walk(root,0);return out.toString().take(12000)}
 fun execute(actions:List<Action>){executor.execute{for(a in actions){when(a.type){"tap"->{if(!findAndTap(a.text))tap(a.x,a.y)};"type"->typeText(a.text);"back"->performGlobalAction(GLOBAL_ACTION_BACK);"home"->performGlobalAction(GLOBAL_ACTION_HOME);"scroll"->scroll(a.direction);"wait"->Thread.sleep((a.x.coerceIn(0f,10f)*1000).toLong())};Thread.sleep(250)}}}
 private fun findAndTap(label:String):Boolean{if(label.isBlank())return false;val root=rootInActiveWindow?:return false;for(n in root.findAccessibilityNodeInfosByText(label)){if(!n.isVisibleToUser)continue;if(n.isClickable)return n.performAction(AccessibilityNodeInfo.ACTION_CLICK);if(n.parent?.isClickable==true)return n.parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)};return false}
 private fun typeText(value:String){val root=rootInActiveWindow?:return;val focused=root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)?:return;val b=Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,value);focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b)}
 private fun tap(x:Float,y:Float){if(x<=0||y<=0)return;val p=Path().apply{moveTo(x,y)};dispatchGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(p,0,50)).build(),null,null)}
 private fun scroll(direction:String){val root=rootInActiveWindow?:return;fun find(n:AccessibilityNodeInfo):AccessibilityNodeInfo?{if(n.isScrollable)return n;for(i in 0 until n.childCount)n.getChild(i)?.let{find(it)?.let{return it}};return null};find(root)?.performAction(if(direction.lowercase()=="up")AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)}
}