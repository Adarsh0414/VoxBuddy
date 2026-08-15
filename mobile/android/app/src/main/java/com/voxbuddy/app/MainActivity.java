package com.voxbuddy.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Registers the native plugin used to detect an already-connected
        // Classic Bluetooth audio device (see AudioDevicePlugin.java) —
        // must happen before super.onCreate() sets up the Capacitor bridge.
        registerPlugin(AudioDevicePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
