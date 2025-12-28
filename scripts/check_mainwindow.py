import importlib
modname='app.views.main_window'
try:
    m = importlib.import_module(modname)
    print('Imported module:', modname)
    print('Has MainWindow?', hasattr(m, 'MainWindow'))
    if hasattr(m,'MainWindow'):
        print('recolor in class dict:', 'recolor_sidebar_icons' in m.MainWindow.__dict__)
        print('dir contains recolor:', any('recolor' in k for k in dir(m.MainWindow)))
        print('getattr class:', getattr(m.MainWindow, 'recolor_sidebar_icons', None))
except Exception as e:
    print('Import error:', e)
    import traceback; traceback.print_exc()
