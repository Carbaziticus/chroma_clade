from flask import Flask, render_template, request, send_from_directory, current_app, redirect, flash
from werkzeug.utils import secure_filename
import os
from check_input import Input, InputError
import random
import chroma_clade

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "storage")
ALIGNMENT_FILE_EXTENSIONS = {"txt", "nex", "fasta", "fas", "fa"}
TREE_FILE_EXTENSIONS = {"txt", "tre", "tree", "xml", "nex", "nexus", "new", "newick"}
MAX_FILE_SIZE_MB = 50
OUTPUT_FILE_PREIX = "col."

app = Flask(__name__)

# TODO could be in config file
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ALIGNMENT_FILE_EXTENSIONS"] = ALIGNMENT_FILE_EXTENSIONS
app.config["TREE_FILE_EXTENSIONS"] = TREE_FILE_EXTENSIONS
app.config["MAX_FILENAME_LENGTH"] = 200  # apparently 255 chars is a common upper limit

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024


def save_file(input_file, file_extensions):
    if not input_file:
        raise ValueError("No file given")
    if not input_file.filename:
        raise ValueError("No filename given")
    if len(input_file.filename) > app.config["MAX_FILENAME_LENGTH"]:
        raise ValueError(f"Length of filename ({input_file.filename}) above max ({app.config['MAX_FILENAME_LENGTH']})")
    if not ('.' in input_file.filename and \
            input_file.filename.rsplit('.', 1)[1].lower() in file_extensions):
        raise ValueError("Filename does not have acceptable file extension")

    saved_name = secure_filename(input_file.filename)  # ensure filename is not dangerous
    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], saved_name)):  # if a file with this name already exists in tmp storage
        saved_name = "-".join([str(random.randint(0, 10000)), saved_name])  # make name unique # TODO use UUID instead?
        if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], saved_name)):  # check it actually is unique
            raise ValueError(
                "Same filename found on system")  # very unlikely to happen by chance, possible security issue
    saved_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_name)
    input_file.save(saved_path)
    return saved_path  # return path so it can be accessed later


#  TODO include file names?
class FormData:

    TREE_IN_FORMATS = ("newick", "nexus")
    ALIGNMENT_IN_FORMATS = ("fasta", "nexus")  # TODO move elsewhere? Could allow larger range anyway
    TREE_OUT_FORMATS = ("figtree", "xml")

    def __init__(self, branches=False, tree_in_format="newick", alignment_in_format="fasta", tree_out_format="figtree",
                 all_sites=True, sites_string="e.g. 1-5, 9, 11-13"):

        if tree_in_format not in FormData.TREE_IN_FORMATS:
            raise ValueError("Tree format not acceptable")
        if alignment_in_format not in FormData.ALIGNMENT_IN_FORMATS:
            raise ValueError("Alignment format not acceptable")
        if tree_out_format not in FormData.TREE_OUT_FORMATS:
            raise ValueError("Output format not acceptable")

        self.data = dict()
        self.data["branches"] = "checked" if branches else ""

        for tree_format in FormData.TREE_IN_FORMATS:
            self.data[f"tree_in_format_{tree_format}"] = "selected" if tree_in_format == tree_format else ""

        for alignment_format in FormData.ALIGNMENT_IN_FORMATS:
            self.data[f"alignment_format_{alignment_format}"] = "selected" if alignment_in_format == alignment_format else ""

        for out_format in FormData.TREE_OUT_FORMATS:
            self.data[f"tree_out_format_{out_format}"] = "selected" if tree_out_format == out_format else ""

        self.data["choose_sites_all"] = "checked" if all_sites else ""
        self.data["choose_sites_range"] = "checked" if not all_sites else ""
        self.data["sites_string"] = sites_string

    def get(self):
        return self.data

    def get_value(self, key):
        return self.data[key]


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':

        # TODO may want to have separate server destinations for alignments, trees and coloured trees for clarity
        tree_file = request.files["tree_file"]
        tree_path = save_file(tree_file, app.config["TREE_FILE_EXTENSIONS"])
        alignment_file = request.files["alignment_file"]
        alignment_path = save_file(alignment_file, app.config["ALIGNMENT_FILE_EXTENSIONS"])

        branches = (request.form.get("branches") is not None)
        align_in_format = request.form["alignment_format"]
        tree_in_format = request.form["tree_format"]
        tree_out_format = request.form["output_format"]
        sites_string = request.form["sites_range"] if request.form["choose_sites"] else ""
        colour_file = os.path.join(os.path.dirname(__file__), Input.DEFAULT_COL_FILE)

        out_dir, out_name = os.path.split(tree_path)
        out_name = OUTPUT_FILE_PREIX + out_name
        out_path = os.path.join(os.path.join(out_dir, out_name))

        try:
            usr_input = Input(tree_path, alignment_path, branches, tree_in_format, align_in_format,
                              colour_file_path=colour_file, output_path=out_path, tree_out_format=tree_out_format,
                              sites_string=sites_string)
        except InputError as e:
            print(e)
            #  flash(str(e), category="warning")
            # TODO want to keep reference to uploaded files too if upload successful and they are validated
            submitted_data = FormData(
                branches=branches, alignment_in_format=align_in_format, tree_in_format=tree_in_format,
                tree_out_format=tree_out_format, sites_string=sites_string,
                all_sites=bool(request.form["choose_sites"]))
            return render_template("index.html", form=submitted_data.get())

        chroma_clade.run(usr_input)
        os.remove(tree_path)
        os.remove(alignment_path)

        return render_template("result.html", out_name=out_name)
        # return send_from_directory(app.config["UPLOAD_FOLDER"], out_name, as_attachment=True)
    print("here")
    return render_template('index.html', form=FormData().get())  # TODO inefficient if making new instance every time


@app.route('/result/<filename>')
def download(filename):
    out_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    # make the output file download and remove it from server;
    # https://stackoverflow.com/questions/40853201/remove-file-after-flask-serves-it

    def generate():
        with open(out_path) as f:
            yield from f

        os.remove(out_path)

    r = current_app.response_class(generate(), mimetype='text/csv')
    r.headers.set('Content-Disposition', 'attachment', filename=filename)
    return r




# TODO must clear files at some point
if __name__ == '__main__':
    app.run(debug=True)
