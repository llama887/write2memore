import glob
import os


def load_styles():
    STYLE_DIRECTORY = "styles/"
    file_list = glob.glob(STYLE_DIRECTORY + "*.css")
    styles: dict[str, str] = {}
    for file_path in file_list:
        with open(file_path, "r") as f:
            print("Storing", os.path.basename(file_path))
            styles[os.path.basename(file_path)] = f.read()
    return styles


def load_js():
    JAVASCRIPT_DIRECTORY = "javascript/"
    file_list = glob.glob(JAVASCRIPT_DIRECTORY + "*.js")
    js: dict[str, str] = {}
    for file_path in file_list:
        with open(file_path, "r") as f:
            print("Storing", os.path.basename(file_path))
            js[os.path.basename(file_path)] = f.read()
    return js


styles = load_styles()
js = load_js()
