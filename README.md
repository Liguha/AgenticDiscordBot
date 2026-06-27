# ...
# Development
Initialize virtual environment:
```bash
conda env create -f manifest.yaml
```

Update virtual environment:
```bash
conda env update -f manifest.yaml --prune
```

Local start:
```bash
conda activate agent_bot
python -m discord_bot
```