Translation files (.mo) should be placed under the following structure:

  app/translations/<lang>/LC_MESSAGES/messages.mo

To generate translations:

1. Extract messages from the code (example):
   xgettext -k_ -o messages.pot $(find app -name '*.py')

2. Create a locale directory and a .po file for the language:
   mkdir -p ar/LC_MESSAGES
   msginit --no-translator -i messages.pot -o ar/LC_MESSAGES/messages.po -l ar

3. Edit `ar/LC_MESSAGES/messages.po` and provide Arabic translations.

4. Compile .po to .mo:
   msgfmt ar/LC_MESSAGES/messages.po -o ar/LC_MESSAGES/messages.mo

When a compiled `messages.mo` is available, the app will use gettext translations automatically. If no compiled translations are present, the app uses a minimal built-in Arabic fallback for demo/testing. Replace the fallback by providing proper `.mo` files for full localization.