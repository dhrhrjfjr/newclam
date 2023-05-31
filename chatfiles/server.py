from flask import Flask, request, make_response, jsonify

from merge import merge_pdfs

import argparse
import os

from chat import (
    create_llama_index,
    get_answer_from_index,
    check_llama_index_exists,
)

from file import (
    get_single_file_upload_path,
    get_index_name_from_single_file_path,
    get_index_name_without_json_extension,
    clean_file,
    single_file_upload_path,
    check_index_exists,
)

app = Flask(__name__)


@app.route("/upload", methods=["POST"])
def upload_file():
    if not request.files:
        return "Please send a POST request with a file", 400

    filepaths = []

    for file in request.files.values():
        uploaded_file = file
        filename = uploaded_file.filename
        filepath = os.path.join(
            get_single_file_upload_path(), os.path.basename(filename)
        )
        uploaded_file.save(filepath)
        filepaths.append(filepath)

    print("filepathssssssssssssssssssssssssssssssss", filepaths)

    if len(filepaths) == 1:
        filepath = filepaths[0]
        if check_llama_index_exists(filepath) is True:
            return get_index_name_without_json_extension(
                get_index_name_from_single_file_path(filepath)
            )

        index_name, index = create_llama_index(filepath)

        clean_file(filepath)
        return (
            make_response(
                {
                    "indexName": get_index_name_without_json_extension(index_name),
                    "indexType": "index",
                }
            ),
            200,
        )

    elif len(filepaths) > 1:
        output_dir = "./documents"
        output_filename = "merged.pdf"
        merge_pdfs(filepaths, output_dir, output_filename)
        output_path = os.path.join(output_dir, output_filename)

        index_name, index = create_llama_index(output_path)

        clean_file(output_path)

        for filepath in filepaths:
            clean_file(filepath)
        return (
            make_response(
                {
                    "indexName": get_index_name_without_json_extension(index_name),
                    "indexType": "index",
                }
            ),
            200,
        )

    else:
        return "No files found in request", 400


@app.route("/query", methods=["GET"])
def query_from_llama_index():
    try:
        message = request.args.get("message")
        index_name = request.args.get("indexName")
        print("\nindex name is ", index_name)
        index_type = request.args.get("indexType")
        print("\nindex type is ", index_type)
        if check_index_exists(index_name) is False:
            return "Index file does not exist", 404

        if index_type == "index":
            answer = get_answer_from_index(message, index_name)

        return make_response(str(answer.response)), 200
    except Exception as e:
        return "Error: {}".format(str(e)), 500


@app.errorhandler(500)
def handle_internal_server_error(e):
    response = {"error": "Internal Server Error", "message": str(e)}
    return jsonify(response), 500


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat Files")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    if not os.path.exists(single_file_upload_path):
        os.makedirs(single_file_upload_path)
    if os.environ.get("CHAT_FILES_MAX_SIZE") is not None:
        app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("CHAT_FILES_MAX_SIZE"))
    app.run(port=5000, host="0.0.0.0", debug=args.debug)
