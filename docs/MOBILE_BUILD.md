# Building VoxBuddy for Android + iOS

## What's actually in `mobile/`

A real Capacitor project — generated with Capacitor's own official CLI in
this environment, not hand-written or faked:

```
mobile/
  capacitor.config.ts   <- points the native shell at your deployed backend
  android/               <- real Android Studio / Gradle project
  ios/                    <- real Xcode project
  resources/              <- source icon/splash images (the amber/teal
                              orb mark, same as the PWA icons)
  www/                    <- placeholder Capacitor's CLI requires; unused,
                              see the note in capacitor.config.ts
```

Icons and splash screens for **both** platforms (every Android density
bucket, every required iOS size) were generated for real using Capacitor's
official asset pipeline (`@capacitor/assets`), not manually faked — you
can see them already sitting in `android/app/src/main/res/mipmap-*/` and
`ios/App/App/Assets.xcassets/`.

## What I could NOT do, and why — be precise about this

This build environment is Linux with no Android SDK and no macOS:

- **`services.gradle.org` returned 403** when the Android project tried to
  download its own Gradle distribution — confirmed by actually running
  `./gradlew tasks` here. So even the Android build couldn't complete in
  this sandbox, not just "wasn't attempted."
- **iOS cannot be built anywhere except on a Mac with Xcode.** This is an
  Apple platform requirement, not a limitation specific to this tool or
  environment — nobody can produce a real, signed iOS build without one,
  regardless of framework (native Swift, React Native, Flutter, Capacitor
  — all of them hit this same wall).

So what you're getting is a **real, correctly-structured, unbuilt**
project — the equivalent of everything up to the point where you'd open
it in the actual IDE. Both platforms need you to do that next step,
because there's no way around needing Android Studio and (separately) a
Mac with Xcode to actually produce something you can put on a device or
submit to a store.

## Before building anything: point it at your real backend

Edit `mobile/capacitor.config.ts` — replace the placeholder URL:
```ts
server: {
  url: 'https://REPLACE-WITH-YOUR-DEPLOYED-BACKEND-URL.onrender.com',
  ...
}
```
with your real deployed backend (see `docs/PLAY_STORE_PUBLISHING.md` Step
1 for deploying to Render). The native app has nothing meaningful to show
until this points at a live server — VoxBuddy needs the WebSocket/API
connection to function at all, there's no offline-first bundle here.

After editing, resync:
```bash
cd mobile
npm install
npx cap sync
```

## Android — on your own machine, with Android Studio installed

1. `cd mobile && npx cap open android` (or just open the `mobile/android`
   folder directly in Android Studio)
2. Let Gradle sync — this is the step that failed here due to network
   restrictions specific to this sandbox; on your normal machine with
   normal internet access it should just work
3. Run on an emulator or your own device to test
4. When ready to publish: Build → Generate Signed Bundle/APK, following
   Android Studio's own signing wizard — **back up that signing key
   somewhere safe**, losing it means you can never update this app
   listing again
5. Continue from Step 5 of `docs/PLAY_STORE_PUBLISHING.md`

## iOS — needs a Mac with Xcode

1. Copy (or clone) this repo onto a Mac
2. Install [Xcode](https://apps.apple.com/us/app/xcode/id497799835) from
   the Mac App Store (free)
3. Install [CocoaPods](https://cocoapods.org): `sudo gem install cocoapods`
4. `cd mobile/ios/App && pod install`
5. Open `App.xcworkspace` (not `.xcodeproj` — important, Capacitor apps
   need the workspace file since CocoaPods is involved) in Xcode
6. Run on the iOS Simulator or your own iPhone to test
7. To publish: you'll need an [Apple Developer account](https://developer.apple.com/programs/)
   ($99/year — this is Apple's own fee, unrelated to anything here),
   then Xcode's Product → Archive → Distribute App flow, uploading to App
   Store Connect

If you don't have access to a Mac, options include: a friend/colleague's
Mac, a cloud Mac rental service (MacStadium, MacinCloud), or a CI service
with macOS runners (GitHub Actions has macOS runners available). I can't
verify any of those services' current pricing/terms — check before
committing to one.

## Native features this scaffold doesn't wire up yet

Capacitor gives native shell + web view; it does NOT automatically give
you native microphone/Bluetooth access beyond what a mobile browser
already provides — for the PRD's actual vision (background audio capture
while the phone is in your pocket, earbud mic routing), you'd add
Capacitor plugins like `@capacitor/microphone` or write a small native
plugin. That's real additional work, scoped honestly as not done here —
this phase only covers "the app installs and loads VoxBuddy as a native
shell," not "background audio capture works better than the browser
already does."
