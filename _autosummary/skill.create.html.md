# skill.create

### skill.create(name, , description='', body='', owner='_local', store=None)

Create a new skill and store it locally.

* **Return type:**
  [`Skill`](skill.base.html.md#skill.base.Skill)

```pycon
>>> import tempfile
>>> from pathlib import Path
>>> store = LocalSkillStore(root=Path(tempfile.mkdtemp()))
>>> s = create('my-skill', description='Does things', store=store)
>>> s.meta.name
'my-skill'
>>> '_local/my-skill' in store
True
```
