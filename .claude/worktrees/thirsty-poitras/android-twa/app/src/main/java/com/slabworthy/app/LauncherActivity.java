package com.slabworthy.app;

import android.content.pm.ActivityInfo;
import android.net.Uri;
import android.os.Bundle;
import androidx.browser.trusted.TrustedWebActivityIntentBuilder;
import androidx.browser.customtabs.CustomTabColorSchemeParams;
import androidx.browser.trusted.TrustedWebActivityIntent;

public class LauncherActivity extends android.app.Activity {

    private static final Uri LAUNCH_URI = Uri.parse("https://slabworthy.com");
    private static final int THEME_COLOR = 0xFF1e1b4b;
    private static final int NAV_COLOR = 0xFF0a0a12;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        CustomTabColorSchemeParams colorScheme = new CustomTabColorSchemeParams.Builder()
                .setToolbarColor(THEME_COLOR)
                .setNavigationBarColor(NAV_COLOR)
                .setNavigationBarDividerColor(NAV_COLOR)
                .build();

        TrustedWebActivityIntentBuilder builder = new TrustedWebActivityIntentBuilder(LAUNCH_URI)
                .setDefaultColorSchemeParams(colorScheme);

        TrustedWebActivityIntent twaIntent = builder.build(null);
        twaIntent.getIntent().addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);

        startActivity(twaIntent.getIntent());
        finish();
    }
}
