from pathlib import Path
import re


def extract_blocks(string):
    text = []
    current_tag = ''
    inside_tag = False
    current_chunk = ''
    inside_chunk = False
    for s in string:
        # find state
        if s == '[':
            inside_chunk = True
            continue
        if s == ']':
            inside_chunk = False
            continue
        if s == '{':
            inside_tag = True
            continue
        if s == '}':
            inside_tag = False

        # fill current
        if inside_chunk:
            current_chunk += s
        if inside_tag and current_chunk:
            current_tag += s

        # add current to text and reinitialize current
        if s == '}' and current_chunk:

            # hack to avoid:
            #   unwanted chunk in case the input has embedded square brackets like so:
            #       [![](image/Tsadra_Credit_Page.png){._idGenObjectAttribute-1}]
            #   strange tags like so:
            #       #RDI-TOK-01-3.xhtml#_idTextAnchor000
            if current_chunk.startswith('!') or current_tag.startswith('#'):
                current_chunk, current_tag = '', ''

            text.append([current_tag, current_chunk])
            current_tag, current_chunk = '', ''

    return text


def cleanup_tags(blocks):
    for i in range(len(blocks)):
        tag = blocks[i][0]

        tag = tag.replace('\n', '')
        tag = re.sub(r'\.?(_idGen)?CharOverride\-[0-9]', '', tag)
        tag = tag.lstrip('.')
        tag = tag.replace('Tibetan-', '')
        tag = tag.strip()

        blocks[i][0] = tag


def concatenate_blocks(blocks):
    out = []
    current_tag = ''
    current_text = ''
    for tag, text in blocks:

        # ignore certain blocks
        if tag.startswith('Front') or tag.startswith('Footnote-Reference'):
            continue
        if tag != current_tag:
            if current_text:
                out.append([current_tag, current_text])

            current_tag = tag
            current_text = text
        else:
            current_text += text

    return out


EQS = {
    'Chapters': 'title1',
    'Book-Title': 'title0',
    'Commentary': 'text',
    'Commentary-Small-Text': 'yigchung',
    'External-Citations': 'quote',
    'Root-Text': 'tsawa',
    'Sabche': 'sapche'
}


def generate_md(blocks):
    ITALICS = '{++*++}'
    BOLD = '{++**++}'
    STRIKE = '{++~~++}'
    HEADER1 = '{++#++}'
    HEADER2 = '{++##++}'
    HEADER3 = '{++###++}'
    out = ''
    for tag, text in blocks:
        if tag == 'text':
            out += text
        if tag == 'yigchung':
            out += ITALICS + text + ITALICS
        if tag == 'tsawa':
            out += BOLD + text + BOLD
        if tag == 'quote':
            out += STRIKE + text + STRIKE
        if tag == 'title0':
            if not text.endswith('\n'):
                text += '\n'
            out += HEADER1 + text
        if tag == 'title1':
            if not text.endswith('\n'):
                text += '\n'
            out += HEADER2 + text
        if tag == 'sapche':
            if not text.endswith('\n'):
                text += '\n'
            out += HEADER3 + text
    return out


def change_tags(blocks):
    return [[EQS[tag], text] for tag, text in blocks]


def main(in_path):
    content = Path(in_path).read_text()
    content = extract_blocks(content)
    cleanup_tags(content)
    content = concatenate_blocks(content)
    content = change_tags(content)
    content = generate_md(content)
    return content


if __name__ == '__main__':
    in_files = Path('input').glob('*.md')
    for i in in_files:
        processed = main(i)
        out_file = Path('output') / (i.stem + '.txt')
        out_file.write_text(processed)