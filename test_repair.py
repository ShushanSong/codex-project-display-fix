import unittest, tempfile, sqlite3, json, importlib.util
from pathlib import Path
from contextlib import closing
spec=importlib.util.spec_from_file_location('repair',Path(__file__).with_name('repair.py'))
repair=importlib.util.module_from_spec(spec); spec.loader.exec_module(repair)

class RecoveryTests(unittest.TestCase):
 def test_preview_and_apply_preserve_chats_and_database(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp); root=home/'example'; root.mkdir()
   db=home/'state_5.sqlite'
   with closing(sqlite3.connect(db)) as c:
    c.execute('create table projects(id text,name text,position integer,created_at_ms integer,updated_at_ms integer)')
    c.execute('create table project_roots(project_id text,position integer,path text)')
    c.execute('insert into projects values(?,?,?,?,?)',('p1','Example',0,1000,2000))
    c.execute('insert into project_roots values(?,?,?)',('p1',0,str(root)))
    c.commit()
   original={'local-projects':{},'pinned-thread-ids':['chat1'],'thread-project-assignments':{'chat1':{'projectId':'keep'}},'unrelated':{'x':1}}
   state=home/'.codex-global-state.json'; state.write_text(json.dumps(original),encoding='utf-8')
   before=state.read_bytes(); db_before=db.read_bytes()
   result=repair.recover(home,apply=False)
   self.assertEqual(result['projects'],1); self.assertEqual(state.read_bytes(),before)
   repair.recover(home,apply=True,check_running=lambda:False)
   current=json.loads(state.read_text(encoding='utf-8'))
   self.assertEqual(current['local-projects']['p1']['rootPaths'],[str(root)])
   self.assertEqual(current['project-order'],['p1'])
   for key in ['pinned-thread-ids','thread-project-assignments','unrelated']:self.assertEqual(current[key],original[key])
   self.assertEqual(db.read_bytes(),db_before)
   self.assertEqual(len(list((home/'backups').glob('project-rootpaths-*'))),1)
   self.assertEqual(repair.recover(home,apply=False)['changed_keys'],[])
 def test_running_app_refuses_write(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(RuntimeError,'running'):
    repair.recover(Path(tmp),apply=True,check_running=lambda:True)

if __name__=='__main__': unittest.main()

