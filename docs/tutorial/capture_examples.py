"""Offscreen captures of the actual shipped UI; no modification of user preferences."""
from pathlib import Path

from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtWidgets import QApplication
from msviewer.window import MainWindow

OUT=Path('tmp/pdfs/guide')
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str((OUT/'settings').resolve()))
app=QApplication([])
window=MainWindow()
window.resize(1600,1120)
window.set_language('zh')
window.show()
scenarios=iter([
    ('sim-ui.png','data/simulated.ms',0,0,(0,1),'Amplitude'),
    ('alma64-ui.png','data/mssel_test_small.ms',1,1,(0,9),'Amplitude'),
    ('alma1-ui.png','data/mssel_test_small.ms',2,None,(0,9),'Imaginary'),
])
state={}

def next_scenario():
    try:
        filename,path,ddid,field,baseline,quantity=next(scenarios)
    except StopIteration:
        window.close();app.quit();return
    state.clear()
    state.update(filename=filename,ddid=ddid,field=field,baseline=baseline,quantity=quantity)
    window.open_ms(path)

def check():
    if window.last_error:
        print(window.last_error,flush=True);app.exit(1);return
    if window.block is None or window._job is not None or window.timer.isActive():
        return
    if not state.get('configured'):
        state['configured']=True
        window.ddid_combo.setCurrentIndex(window.ddid_combo.findData(state['ddid']))
        window.field_combo.setCurrentIndex(window.field_combo.findData(state['field']))
        window.baseline_combo.setCurrentIndex(next(i for i in range(window.baseline_combo.count())
             if window.baseline_combo.itemData(i)==state['baseline']))
        window.quantity_combo.setCurrentIndex(window.quantity_combo.findData(state['quantity']))
        window.request_read()
    elif not state.get('captured'):
        state['captured']=True
        QTimer.singleShot(150,save)

def save():
    assert window.grab().save(str(OUT/state['filename']))
    print(state['filename'],window.block.values.shape,flush=True)
    window.block=None
    QTimer.singleShot(0,next_scenario)

timer=QTimer()
timer.timeout.connect(check);timer.start(100)
QTimer.singleShot(0,next_scenario)
QTimer.singleShot(30000,lambda:app.exit(2))
raise SystemExit(app.exec())
