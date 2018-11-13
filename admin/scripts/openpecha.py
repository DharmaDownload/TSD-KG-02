from pathlib import Path
from admin.scripts.formatted_dmp import FormattedDMP
import re
import copy


class Patches:
    def __init__(self):
        self.modes = ['dergepage', 'cm']

    def clean(self, patches, mode):
        assert mode in self.modes, 'The given mode is not valid. Options are: ' + str(self.modes)

        if mode == 'dergepage':
            return self.clean_patches(patches, self.is_dergepage_diff, self.find_dergepage_str)
        elif mode == 'cm':
            return self.clean_patches(patches, self.is_cm_diff, self.find_cm_str)

    @staticmethod
    def is_dergepage_diff(diff):
        op, text = diff
        return op == 1 and '[' in text and ']' in text

    @staticmethod
    def find_dergepage_str(text):
        regex = r'(\\\[.*?\\\])'
        match = re.findall(regex, text)
        return match[0] if match else None

    @staticmethod
    def is_cm_diff(diff):
        op, text = diff
        return op == 1 and ('{' in text or '}' in text)

    @staticmethod
    def find_cm_str(text):
        # nothing to do
        return text

    @staticmethod
    def clean_patches(orig_patches, is_needed_diff, find_needed_str):
        """
        Selects and cleans a given patch list using functions given as arguments
        Intended for patches generated by Google's diff_match_patch module.

        :param orig_patches: original set of patches
        :type orig_patches: patch objects created with DMP.patch_make(str, str)
        :param is_needed_diff: test to see if a diff contains a wanted modification
        :type is_needed_diff: funct returning a boolean
        :param find_needed_str: finds the parts of the diff that are to keep
        :type find_needed_str: funct returning the replacement str
        :return: filtered set of patches that only contain the needed modifications
        """
        new_patches = []
        for patch in orig_patches:
            keep = False
            new_diffs = []
            for diff in patch.diffs:

                # find diff to modify
                if is_needed_diff(diff):
                    op, text = diff
                    needed = find_needed_str(text)
                    if needed:
                        new_diffs.append((op, needed))
                        keep = True

                # Important: keep the diffs with no modification used as context
                # (used by DMP to calculate the correct patching location)
                elif diff[0] == 0:
                    new_diffs.append(diff)

            # select only relevant patches
            if keep:
                patch.diffs = new_diffs  # replace the old diffs with the modified ones
                new_patches.append(patch)

        return new_patches

    @staticmethod
    def _deconstruct_cm_patch(patch):
        before = []
        cm = []
        after = []
        state = -1
        for diff in patch.diffs:
            string = diff[1]
            if '{' in string:
                state = 0

            if state == -1:
                before.append(diff)
            elif state == 0:
                cm.append(diff)
            elif state == 1:
                after.append(diff)
            else:
                raise ValueError('this should not happen.')

            if '}' in string:
                state = 1
        return before, cm, after

    def format_cm_operations(self, patches):
        for patch in patches:
            before, cm, after = self._deconstruct_cm_patch(patch)
            if cm:
                # process diffs
                string = ''.join([c[1] for c in cm])
                op = string[1]
                string = string.replace('{', '')\
                               .replace('}', '')\
                               .replace('~', '')\
                               .replace('+', '')\
                               .replace('-', '')

                if op == '+':
                    cm = [(1, string)]
                elif op == '-':
                    cm = [(-1, string)]
                elif op == '~':
                    to_del, to_add = string.split('>')
                    cm = [(-1, to_del), (1, to_add)]
                else:
                    raise ValueError('this should not happen')

                # replace old diffs with new diffs
                patch.diffs = before + cm + after

        return patches


class OpenPecha:
    def __init__(self, dirs_conf):
        self.dmp = FormattedDMP()
        self.cp = Patches()
        self.dirs = self.set_dirs(dirs_conf)
        self.current = {'name': '', 'base': None, 'layers': {}}

    @staticmethod
    def set_dirs(dir_paths):
        """
        populates self.dirs and creates the corresponding folder scaffolding
        :param dir_paths: paths as strings
        :return: content of self.dirs
        """
        dirs = {'bases': Path('../../') / dir_paths['bases'],
                'layers': Path('../../') / dir_paths['layers'],
                'input': Path('../../') / dir_paths['input'],
                'output': Path('../../') / dir_paths['output']}
        dirs['bases'].mkdir(exist_ok=True)
        dirs['layers'].mkdir(exist_ok=True)
        dirs['input'].mkdir(exist_ok=True)
        dirs['output'].mkdir(exist_ok=True)
        return dirs

    def reset_current(self):
        self.current = {'base': None, 'layers': {}}

    def load_pecha(self, pch_path):
        """
        loads in self.current all the files pertaining to the current layered text
        :param pch_path: the base-name of the layered text to load
        """
        assert pch_path in [b.stem for b in self.dirs['bases'].glob('*.txt')], f'base file missing for {pch_path}'
        assert pch_path in [b.name for b in self.dirs['layers'].glob('*') if b.is_dir()], \
            f'folder of layers missing for {pch_path}'

        base = self.dirs['bases'] / f'{pch_path}.txt'
        self.current['name'] = pch_path
        self.current['base'] = base.read_text(encoding='utf-8-sig')

        lyrs = self.dirs['layers'] / pch_path
        for lyr in lyrs.glob('*.*'):
            lyr_type, lyr_name = lyr.suffix[1:], lyr.stem
            if lyr_name not in self.current['layers']:
                self.current['layers'][lyr_name] = {}
            self.current['layers'][lyr_name][lyr_type] = lyr.read_text(encoding='utf-8-sig')

    @staticmethod
    def build_md_layers(text):
        """

        :param text: string to be analyzed
        :return: the base string and a list of name/layer tuples.
        :rtype: str, [(str, str), ...]
        """
        chunks = re.split(r'{([+\-~]{2}(?:.|\n)+?)[+\-~]{2}}', text)
        base = [chunks[i] for i in range(0, len(chunks), 2)]
        base = ''.join(base)

        lyrs = {'title1': [],
                'title2': [],
                'sapche': [],
                'tsawa': [],
                'quotes': [],
                'yigchung': []}

        mod_idx = list(range(1, len(chunks), 2))
        for num, c in enumerate(chunks):
            if num in mod_idx:
                if c.startswith('++'):
                    c = c[2:]
                    if c == '*':  # test for yigchung
                        lyrs['yigchung'].append(c)
                    elif c == '**':
                        lyrs['tsawa'].append(c)
                    elif c == '~~':
                        lyrs['quotes'].append(c)
                    elif c == '###':
                        lyrs['sapche'].append(c)
                    elif c == '##':
                        lyrs['title2'].append(c)
                    elif c == '#':
                        lyrs['title1'].append(c)
                    elif c.startswith('='):  # test for titles (to be improved)
                        lyrs['title1'].append(c)
                else:
                    raise ValueError('This should not happen: the file used to create an openpecha is')
            else:
                for k in lyrs.keys():
                    lyrs[k].append(c)

        return base, [(k, ''.join(v)) for k, v in lyrs.items()]

    def new_pecha(self, basename):
        """
        Create the scafolding for a new layered text:
            - <basename>.txt        the base layer
            - layers/<basename>/    the layer's folder
        """
        basename = self.dirs['input'] / basename
        assert basename.is_file() and basename.suffix == '.txt', f'{basename} is not found in {self.dirs["input"]}.'
        dump = basename.read_text(encoding='utf-8-sig')

        # separate base from title and yigchung
        base, md_lyrs = self.build_md_layers(dump)

        # write base
        Path(self.dirs['bases'] / f'{basename.stem}.txt').write_text(base, encoding='utf-8-sig')

        # write layers
        lyr_dir = Path(self.dirs['layers'] / basename.stem)
        lyr_dir.mkdir(exist_ok=True)

        self.load_pecha(basename.stem)
        for name, lyr in md_lyrs:
            self.create_layer(base, lyr, name, clean_patch=False)

    def create_layer(self, orig, mod, name, deps='', clean_patch=True):
        """
        TODO: should not need orig argument. should build against the base in self.current
        creates and writes to file a new layer
        :param orig: the original text
        :type orig: str
        :param mod: the modified text
                    (contains the modifications to be turned into a layer)
        :type mod: str
        :param name: the name of the new layer
        :type name: str
        :param deps: the dependency of the new layer. layers are separated by "\n"s
        :param clean_patch:
        """
        lyr = self.dmp.patch_make(orig, mod)
        lyr = self.cp.clean(lyr, 'cm') if clean_patch else lyr
        lyr = self.cp.format_cm_operations(lyr)
        lyr = '\n'.join([self.dmp.decode_patch(str(p)) for p in lyr])

        lyr_file = self.dirs['layers'] / self.current['name'] / f'{name}.layer'
        lyr_file.write_text(lyr, encoding='utf-8-sig')

        if deps:
            dep_file = self.dirs['layers'] / self.current['name'] / f'{name}.deps'
            dep_file.write_text(deps, encoding='utf-8-sig')

    @staticmethod
    def _format_notes(patches):
        footnotes = ''
        for num, patch in enumerate(patches):
            diffs = patch.diffs
            assert len(diffs) == 3 or len(diffs) == 4, 'unexpected diff'
            mod = diffs[1:-1]
            p_type = [d[0] for d in mod]
            strings = [d[1] for d in mod]
            if p_type == [-1, 1]:
                note = '>>'.join(strings)
            elif p_type == [1]:
                note = '+' + ''.join(strings)

            elif p_type == [-1]:
                note = '-' + ''.join(strings)
            else:
                raise ValueError('this should not happen')
            if note:
                diffs.insert(-1, (1, f'[^{num+1}]'))
                footnotes += f'\n[^{num+1}]: ' + note

        return footnotes, patches

    def create_view(self, layers, mode=None, cor_as_note=True):
        view = copy.deepcopy(self.current['base'])
        fails = {}
        footnotes = ''

        for lyr_name in layers:
            lyr_str = self.current['layers'][lyr_name]['layer']
            lyr = self.dmp.patch_fromText(lyr_str)
            if cor_as_note and lyr_name == 'correction':
                footnotes, lyr = self._format_notes(lyr)

            view, res = self.dmp.patch_apply(lyr, view, mode)
            mstk = {}
            for num, r in enumerate(res):
                if not r:
                    mstk[str(num+1)] = self.dmp.format_patch(lyr[num])
            if mstk:
                fails[lyr_name] = mstk

        footnotes = '\n\n' + footnotes if footnotes else footnotes
        return view + footnotes, fails

    def write_views(self, layers, view_type):
        if view_type == 'export':
            view, fails = self.create_view(layers)
        elif view_type == 'edit':
            view, fails = self.create_view(layers, mode='CM')
        else:
            raise ValueError('this should not happen.')

        out = self.dirs['output'] / f'{self.current["name"]}_export_{"+".join(layers)}.txt'
        out.write_text(view, encoding='utf-8-sig')
        if fails:
            out = self.dirs['output'] / f'{self.current["name"]}_export_{"+".join(layers)}_mistakes.txt'
            out.write_text(str(fails), encoding='utf-8-sig')


if __name__ == '__main__':
    # basic usecase
    conf = {
        'bases': 'plaintext',
        'layers': 'admin/layers',
        'input': 'user/edited',
        'output': 'user/output'
    }

    existing = OpenPecha(conf)
    # existing.new_pecha('test_base+md.txt')
    #
    # existing.create_layer(existing.current['base'],
    #                       Path(existing.dirs['input'] / 'text_base+md_correction.txt').read_text(encoding='utf-8-sig'),
    #                       'correction')
    #
    # to_apply = ['italics', 'title', 'correction']
    # existing.write_views(to_apply, 'edit')
    # existing.write_views(to_apply, 'export')
    # existing.reset_current()

    existing.new_pecha('TSD-KG-02.txt')
    to_apply = ['tsawa', 'yigchung', 'quotes', 'sapche']
    existing.write_views(to_apply, 'export')

