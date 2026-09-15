package com.whisper.wowlauncher;

import android.app.Activity;
import android.app.role.RoleManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.provider.MediaStore;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.Collator;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int ORANGE = Color.rgb(233, 84, 32);
    private static final int AUBERGINE = Color.rgb(94, 39, 80);
    private static final int PANEL = Color.argb(150, 35, 15, 31);
    private static final int SOFT_WHITE = Color.rgb(245, 242, 244);

    private final Handler clockHandler = new Handler();
    private final ArrayList<AppEntry> apps = new ArrayList<>();
    private FrameLayout root;
    private LinearLayout home;
    private LinearLayout drawer;
    private GridLayout drawerGrid;
    private TextView timeView;
    private TextView dateView;
    private float touchDownY;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(AUBERGINE);
        window.setNavigationBarColor(Color.rgb(44, 16, 38));

        loadApps();
        buildUi();
        startClock();
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadApps();
        if (drawer != null && drawer.getVisibility() == View.VISIBLE) {
            populateDrawer("");
        }
    }

    @Override
    protected void onDestroy() {
        clockHandler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }

    @Override
    public void onBackPressed() {
        if (drawer != null && drawer.getVisibility() == View.VISIBLE) {
            hideDrawer();
        } else {
            super.onBackPressed();
        }
    }

    private void buildUi() {
        root = new FrameLayout(this);
        root.setBackgroundResource(com.whisper.wowlauncher.R.drawable.ubuntu_wallpaper);
        root.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                touchDownY = event.getY();
                return true;
            }
            if (event.getAction() == MotionEvent.ACTION_UP) {
                float dy = event.getY() - touchDownY;
                if (dy < -120) showDrawer();
                if (dy > 120 && drawer.getVisibility() == View.VISIBLE) hideDrawer();
                return true;
            }
            return true;
        });

        buildHome();
        buildDrawer();
        setContentView(root);
    }

    private void buildHome() {
        home = new LinearLayout(this);
        home.setOrientation(LinearLayout.VERTICAL);
        home.setPadding(dp(18), dp(18), dp(18), dp(18));
        root.addView(home, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        LinearLayout topBar = new LinearLayout(this);
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand = pill("●  WoW Ubuntu", ORANGE);
        topBar.addView(brand, new LinearLayout.LayoutParams(0, dp(40), 1f));

        TextView defaultButton = pill("Set default", Color.argb(185, 255, 255, 255));
        defaultButton.setTextColor(Color.rgb(55, 30, 48));
        defaultButton.setOnClickListener(v -> requestDefaultLauncher());
        topBar.addView(defaultButton, new LinearLayout.LayoutParams(dp(112), dp(40)));
        home.addView(topBar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(44)));

        LinearLayout clockBox = new LinearLayout(this);
        clockBox.setOrientation(LinearLayout.VERTICAL);
        clockBox.setPadding(dp(4), dp(38), dp(4), dp(26));
        timeView = new TextView(this);
        timeView.setTextColor(Color.WHITE);
        timeView.setTextSize(54);
        timeView.setGravity(Gravity.CENTER);
        timeView.setShadowLayer(10, 0, 3, Color.argb(110, 0, 0, 0));
        dateView = new TextView(this);
        dateView.setTextColor(Color.argb(220, 255, 255, 255));
        dateView.setTextSize(16);
        dateView.setGravity(Gravity.CENTER);
        clockBox.addView(timeView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        clockBox.addView(dateView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        home.addView(clockBox, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView section = new TextView(this);
        section.setText("Apps");
        section.setTextColor(Color.WHITE);
        section.setTextSize(16);
        section.setPadding(dp(4), dp(10), 0, dp(10));
        home.addView(section);

        GridLayout favorites = new GridLayout(this);
        favorites.setColumnCount(4);
        favorites.setUseDefaultMargins(false);
        int count = Math.min(8, apps.size());
        for (int i = 0; i < count; i++) {
            favorites.addView(appCell(apps.get(i), false), gridParams(4, dp(92)));
        }
        home.addView(favorites, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        home.addView(buildDock(), new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(94)));
    }

    private View buildDock() {
        LinearLayout dockWrap = new LinearLayout(this);
        dockWrap.setPadding(dp(8), dp(8), dp(8), dp(8));
        dockWrap.setGravity(Gravity.CENTER);
        dockWrap.setBackground(roundRect(PANEL, 28));

        addQuickAction(dockWrap, "Phone", new Intent(Intent.ACTION_DIAL, Uri.parse("tel:")), null);
        addQuickAction(dockWrap, "Message", new Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:")), null);
        addQuickAction(dockWrap, "Browser", new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com")), null);
        addQuickAction(dockWrap, "Camera", new Intent(MediaStore.ACTION_IMAGE_CAPTURE), null);
        addQuickAction(dockWrap, "Apps", null, v -> showDrawer());
        return dockWrap;
    }

    private void addQuickAction(LinearLayout parent, String label, Intent intent, View.OnClickListener custom) {
        LinearLayout cell = new LinearLayout(this);
        cell.setOrientation(LinearLayout.VERTICAL);
        cell.setGravity(Gravity.CENTER);
        cell.setPadding(dp(4), dp(3), dp(4), dp(3));

        ImageButton icon = new ImageButton(this);
        icon.setBackground(roundRect(Color.argb(100, 255, 255, 255), 22));
        icon.setPadding(dp(10), dp(10), dp(10), dp(10));
        if (intent != null) {
            ResolveInfo info = getPackageManager().resolveActivity(intent, PackageManager.MATCH_DEFAULT_ONLY);
            if (info != null) icon.setImageDrawable(info.loadIcon(getPackageManager()));
        } else {
            icon.setImageResource(com.whisper.wowlauncher.R.drawable.launcher_icon);
        }
        icon.setScaleType(android.widget.ImageView.ScaleType.FIT_CENTER);

        View.OnClickListener listener = custom != null ? custom : v -> safeStart(intent);
        icon.setOnClickListener(listener);
        cell.setOnClickListener(listener);

        TextView text = new TextView(this);
        text.setText(label);
        text.setTextColor(Color.WHITE);
        text.setTextSize(11);
        text.setGravity(Gravity.CENTER);
        text.setSingleLine(true);
        cell.addView(icon, new LinearLayout.LayoutParams(dp(48), dp(48)));
        cell.addView(text, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(24)));
        parent.addView(cell, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));
    }

    private void buildDrawer() {
        drawer = new LinearLayout(this);
        drawer.setOrientation(LinearLayout.VERTICAL);
        drawer.setPadding(dp(16), dp(16), dp(16), dp(8));
        drawer.setBackgroundColor(Color.rgb(34, 20, 31));
        drawer.setVisibility(View.GONE);
        drawer.setClickable(true);

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        TextView title = new TextView(this);
        title.setText("All Apps");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        header.addView(title, new LinearLayout.LayoutParams(0, dp(52), 1f));

        TextView close = pill("⌄", Color.argb(70, 255, 255, 255));
        close.setTextSize(25);
        close.setOnClickListener(v -> hideDrawer());
        header.addView(close, new LinearLayout.LayoutParams(dp(52), dp(44)));
        drawer.addView(header);

        EditText search = new EditText(this);
        search.setHint("Search apps");
        search.setHintTextColor(Color.argb(150, 255, 255, 255));
        search.setTextColor(Color.WHITE);
        search.setSingleLine(true);
        search.setPadding(dp(16), 0, dp(16), 0);
        search.setBackground(roundRect(Color.argb(55, 255, 255, 255), 20));
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) { }
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { populateDrawer(s.toString()); }
            @Override public void afterTextChanged(Editable s) { }
        });
        drawer.addView(search, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50)));

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        drawerGrid = new GridLayout(this);
        drawerGrid.setColumnCount(4);
        drawerGrid.setPadding(0, dp(12), 0, dp(20));
        scroll.addView(drawerGrid, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        drawer.addView(scroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        root.addView(drawer, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        populateDrawer("");
    }

    private void populateDrawer(String query) {
        if (drawerGrid == null) return;
        drawerGrid.removeAllViews();
        String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
        for (AppEntry app : apps) {
            if (q.length() == 0 || app.label.toLowerCase(Locale.ROOT).contains(q)) {
                drawerGrid.addView(appCell(app, true), gridParams(4, dp(98)));
            }
        }
    }

    private View appCell(AppEntry app, boolean drawerMode) {
        LinearLayout cell = new LinearLayout(this);
        cell.setOrientation(LinearLayout.VERTICAL);
        cell.setGravity(Gravity.CENTER);
        cell.setPadding(dp(3), dp(6), dp(3), dp(4));
        cell.setClickable(true);

        ImageButton icon = new ImageButton(this);
        icon.setImageDrawable(app.icon);
        icon.setScaleType(android.widget.ImageView.ScaleType.FIT_CENTER);
        icon.setPadding(dp(7), dp(7), dp(7), dp(7));
        icon.setBackground(roundRect(Color.argb(drawerMode ? 28 : 42, 255, 255, 255), 20));
        icon.setOnClickListener(v -> launch(app));
        cell.addView(icon, new LinearLayout.LayoutParams(dp(56), dp(56)));

        TextView label = new TextView(this);
        label.setText(app.label);
        label.setTextColor(SOFT_WHITE);
        label.setTextSize(11);
        label.setGravity(Gravity.CENTER);
        label.setMaxLines(1);
        label.setEllipsize(android.text.TextUtils.TruncateAt.END);
        label.setPadding(dp(2), dp(3), dp(2), 0);
        cell.addView(label, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(28)));
        cell.setOnClickListener(v -> launch(app));
        return cell;
    }

    private GridLayout.LayoutParams gridParams(int columns, int height) {
        int screen = getResources().getDisplayMetrics().widthPixels - dp(32);
        GridLayout.LayoutParams p = new GridLayout.LayoutParams();
        p.width = Math.max(dp(72), screen / columns);
        p.height = height;
        return p;
    }

    private void loadApps() {
        apps.clear();
        PackageManager pm = getPackageManager();
        Intent launcherIntent = new Intent(Intent.ACTION_MAIN);
        launcherIntent.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> resolved = pm.queryIntentActivities(launcherIntent, 0);
        for (ResolveInfo info : resolved) {
            if (info.activityInfo == null) continue;
            if (getPackageName().equals(info.activityInfo.packageName)) continue;
            String label = String.valueOf(info.loadLabel(pm));
            Drawable icon = info.loadIcon(pm);
            apps.add(new AppEntry(label, info.activityInfo.packageName, info.activityInfo.name, icon));
        }
        final Collator collator = Collator.getInstance();
        Collections.sort(apps, new Comparator<AppEntry>() {
            @Override public int compare(AppEntry a, AppEntry b) { return collator.compare(a.label, b.label); }
        });
    }

    private void launch(AppEntry app) {
        try {
            Intent intent = new Intent(Intent.ACTION_MAIN);
            intent.addCategory(Intent.CATEGORY_LAUNCHER);
            intent.setComponent(new ComponentName(app.packageName, app.className));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            startActivity(intent);
            hideDrawer();
        } catch (Exception e) {
            Toast.makeText(this, "Could not open " + app.label, Toast.LENGTH_SHORT).show();
        }
    }

    private void safeStart(Intent intent) {
        if (intent == null) return;
        try {
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, "No compatible app found", Toast.LENGTH_SHORT).show();
        }
    }

    private void requestDefaultLauncher() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                RoleManager roleManager = (RoleManager) getSystemService(Context.ROLE_SERVICE);
                if (roleManager != null && roleManager.isRoleAvailable(RoleManager.ROLE_HOME)) {
                    if (!roleManager.isRoleHeld(RoleManager.ROLE_HOME)) {
                        startActivityForResult(roleManager.createRequestRoleIntent(RoleManager.ROLE_HOME), 120);
                    } else {
                        Toast.makeText(this, "WoW Ubuntu Launcher is already your Home app", Toast.LENGTH_SHORT).show();
                    }
                    return;
                }
            }
            startActivity(new Intent(Settings.ACTION_HOME_SETTINGS));
        } catch (Exception e) {
            Intent chooser = new Intent(Intent.ACTION_MAIN);
            chooser.addCategory(Intent.CATEGORY_HOME);
            startActivity(chooser);
        }
    }

    private void showDrawer() {
        if (drawer == null) return;
        populateDrawer("");
        drawer.setAlpha(0f);
        drawer.setTranslationY(dp(70));
        drawer.setVisibility(View.VISIBLE);
        drawer.animate().alpha(1f).translationY(0).setDuration(180).start();
    }

    private void hideDrawer() {
        if (drawer == null || drawer.getVisibility() != View.VISIBLE) return;
        drawer.animate().alpha(0f).translationY(dp(70)).setDuration(150).withEndAction(() -> {
            drawer.setVisibility(View.GONE);
            drawer.setAlpha(1f);
            drawer.setTranslationY(0);
        }).start();
    }

    private void startClock() {
        Runnable tick = new Runnable() {
            @Override public void run() {
                Date now = new Date();
                if (timeView != null) timeView.setText(new SimpleDateFormat("HH:mm", Locale.getDefault()).format(now));
                if (dateView != null) dateView.setText(new SimpleDateFormat("EEEE, d MMMM", Locale.getDefault()).format(now));
                clockHandler.postDelayed(this, 1000);
            }
        };
        clockHandler.post(tick);
    }

    private TextView pill(String text, int color) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextColor(Color.WHITE);
        v.setTextSize(13);
        v.setGravity(Gravity.CENTER);
        v.setPadding(dp(12), 0, dp(12), 0);
        v.setBackground(roundRect(color, 20));
        return v;
    }

    private GradientDrawable roundRect(int color, int radiusDp) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(dp(radiusDp));
        return d;
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }

    private static class AppEntry {
        final String label;
        final String packageName;
        final String className;
        final Drawable icon;

        AppEntry(String label, String packageName, String className, Drawable icon) {
            this.label = label;
            this.packageName = packageName;
            this.className = className;
            this.icon = icon;
        }
    }
}
