import os

from src.utils import find_single_prm_file, parse_prm_file


# todo this does a lot of implicit error throwing, check it in the function itself and give proper error messages
def move_benchmark_files(from_loc: str, to: str) -> None:
    prm_path = find_single_prm_file(from_loc)
    prm = parse_prm_file(prm_path)

    # todo generalise this, don't treat each field separately
    vtkOutput = prm["Parameters"]["vtk_output"]
    newVtkOutput = os.path.join(to, 'vtk')

    with open(prm_path) as f:
        prm_text = f.read()

    prm_text = prm_text.replace(vtkOutput, newVtkOutput)

    with open(prm_path, 'w') as f:
        f.write(prm_text)

    os.rename(from_loc, to)
