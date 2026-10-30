from pathlib import Path
import nbformat
from nbclient import NotebookClient
root=Path(__file__).resolve().parents[1]
path=root/"notebooks/01_multi_asset_research.ipynb"
notebook=nbformat.read(path,as_version=4)
NotebookClient(notebook,timeout=180,kernel_name="python3",resources={"metadata":{"path":str(root)}}).execute()
# The tracked notebook remains clean; full executed output stays local.
target=root/"reports/local/executed_research.ipynb"
target.parent.mkdir(parents=True,exist_ok=True)
nbformat.write(notebook,target)
print(f"Executed {sum(c.cell_type=='code' for c in notebook.cells)} code cells: {target}")
