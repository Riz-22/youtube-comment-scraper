thonimport json

def export_comments(comments, output_format='json'):
    if output_format == 'json':
        with open('comments_output.json', 'w') as f:
            json.dump(comments, f, indent=4)
    else:
        print("Unsupported format")