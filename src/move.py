import os

from src.utils import parse_prm_file, find_prm_files


# todo this does a lot of implicit error throwing, check it in the function itself and give proper error messages
def move_benchmark_files(from_loc: str, to: str) -> None:
    prm_paths = find_prm_files(from_loc)

    for path in prm_paths:
        with open(path, "r") as f:
            prm_content = f.read()

        prm = parse_prm_file(prm_content)

        # todo generalise this, don't treat each field separately
        vtkOutput = prm["Parameters"]["vtk_output"]
        newVtkOutput = os.path.join(to, 'vtk')

        with open(path) as f:
            prm_text = f.read()

        prm_text = prm_text.replace(vtkOutput, os.path.abspath(newVtkOutput))

        with open(path, 'w') as f:
            f.write(prm_text)

    os.rename(from_loc, to)


# from_loc must be a directory
# to must not be inside from_loc
def move_benchmark_folders(from_loc: str, to: str) -> None:
    is_benchmark_suite = len(find_prm_files(from_loc)) > 0

    if is_benchmark_suite:
        move_benchmark_files(from_loc, to)
    else:
        os.makedirs(to, exist_ok=True)

        files = list(os.scandir(from_loc))
        plain_files = filter(lambda f: f.is_file(), files)
        for f in plain_files:
            os.rename(f.path, os.path.join(to, f.name))

        directories = filter(lambda f: f.is_dir(), files)
        for d in directories:
            move_benchmark_folders(d.path, os.path.join(to, d.name))

        # from_loc should be empty now
        os.rmdir(from_loc)
