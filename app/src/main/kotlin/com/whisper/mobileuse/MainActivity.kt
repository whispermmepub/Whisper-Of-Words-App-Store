package com.whisper.mobileuse
import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.*
import java.util.concurrent.Executors
class MainActivity:Activity(){
 private val prefs by lazy{getSharedPreferences("mobile_use",0)}
 private val executor=Executors.newSingleThreadExecutor()
 private lateinit var endpoint:EditText;private lateinit var key:EditText;private lateinit var command:EditText;private lateinit var log:TextView
 override fun onCreate(b:Bundle?){super.onCreate(b);val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(28,28,28,28)}
 val title=TextView(this).apply{text="Mobile Use";textSize=28f};endpoint=EditText(this).apply{hint="LLM endpoint";setText(prefs.getString("endpoint","https://api.openai.com/v1/chat/completions"))};key=EditText(this).apply{hint="API key (stored locally)";inputType=0x81};command=EditText(this).apply{hint="Tell Mobile Use what to do";minLines=3};log=TextView(this)
 val save=Button(this).apply{text="Save API settings"};val access=Button(this).apply{text="Enable Accessibility"};val run=Button(this).apply{text="Run"}
 save.setOnClickListener{prefs.edit().putString("endpoint",endpoint.text.toString().trim()).putString("key",key.text.toString()).apply();log.text="Saved locally."}
 access.setOnClickListener{startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}
 run.setOnClickListener{val s=AgentAccessibilityService.instance;val task=command.text.toString().trim();if(s==null){log.text="Enable Mobile Use in Accessibility settings first.";return@setOnClickListener};if(task.isEmpty()){log.text="Enter a task.";return@setOnClickListener};log.text="Planning...";executor.execute{val p=LlmClient.plan(this,task,s.snapshot());runOnUiThread{log.text=p.message};if(p.actions.isNotEmpty())s.execute(p.actions)}}
 root.addView(title);root.addView(endpoint);root.addView(key);root.addView(save);root.addView(access);root.addView(command);root.addView(run);root.addView(log);val capture=Button(this).apply{text="Allow Screen Capture"}
  capture.setOnClickListener{ScreenCaptureManager.request(this@MainActivity)}
  root.addView(capture)
  setContentView(root)}
}