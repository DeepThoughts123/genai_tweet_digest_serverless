* Count lines of code in the project:
```
git ls-files | xargs wc -l
```

* Include a specific folder (e.g. algorithms/llm-agent) in python's import search path:
```
export PYTHONPATH=$PYTHONPATH:/path/to/your/project/algorithms/llm-agent
```

* Run a specific test file:
```
pytest tests/test_tweet_categorizer.py
```