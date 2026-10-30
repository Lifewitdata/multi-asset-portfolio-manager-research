"""Alternative for sandboxed runners without kernel sockets; runs every cell via IPython."""
from pathlib import Path
import os
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
root=Path(__file__).resolve().parents[1]
os.chdir(root)
nb=nbformat.read(root/'notebooks/01_multi_asset_research.ipynb',as_version=4)
shell=InteractiveShell.instance()
import matplotlib
matplotlib.use('module://matplotlib_inline.backend_inline')
from matplotlib_inline.backend_inline import configure_inline_support
configure_inline_support(shell, 'inline')
count=0
for cell in nb.cells:
    if cell.cell_type!='code':continue
    count+=1
    with capture_output() as captured:
        result=shell.run_cell(cell.source,store_history=True)
    if result.error_before_exec or result.error_in_exec:
        raise RuntimeError(f'Notebook cell {count} failed') from (result.error_before_exec or result.error_in_exec)
    cell.execution_count=count
    outputs=[]
    if captured.stdout:outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
    if captured.stderr:outputs.append(nbformat.v4.new_output('stream',name='stderr',text=captured.stderr))
    outputs.extend(nbformat.v4.new_output('display_data',data=o.data,metadata=o.metadata) for o in captured.outputs)
    cell.outputs=outputs
folder=root/'reports/local';folder.mkdir(parents=True,exist_ok=True)
nbformat.write(nb,folder/'executed_research.ipynb')
print(f'Executed {count} code cells in-process; captured {sum(len(c.get("outputs",[])) for c in nb.cells)} outputs.')
