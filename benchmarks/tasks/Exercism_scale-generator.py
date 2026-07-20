"""Exercism task Exercism_scale-generator"""
from pathlib import Path

TASK = """Implement the solution defined in scale_generator.py. Make the tests pass.

Instructions:
# Instructions

## Chromatic Scales

Scales in Western music are based on the chromatic (12-note) scale.
This scale can be expressed as the following group of pitches:

> A, A♯, B, C, C♯, D, D♯, E, F, F♯, G, G♯

A given sharp note (indicated by a ♯) can also be expressed as the flat of the note above it (indicated by a ♭) so the chromatic scale can also be written like this:

> A, B♭, B, C, D♭, D, E♭, E, F, G♭, G, A♭

The major and minor scale and modes are subsets of this twelve-pitch collection.
They have seven pitches, and are called diatonic scales.
The collection of notes in these scales is written with either sharps or flats, depending on the tonic (starting note).
Here is a table indicating whether the flat expression or sharp expression of the scale would be used for a given tonic:

| Key Signature | Major                 | Minor                |
| ------------- | --------------------- | -------------------- |
| Natural       | C                     | a                    |
| Sharp         | G, D, A, E, B, F♯     | e, b, f♯, c♯, g♯, d♯ |
| Flat          | F, B♭, E♭, A♭, D♭, G♭ | d, g, c, f, b♭, e♭   |

Note that by common music theory convention the natural notes "C" and "a" follow the sharps scale when ascending and the flats scale when descending.
For the scope of this exercise the scale is only ascending.

### Task

Given a tonic, generate the 12 note chromatic scale starting with the tonic.

- Shift the base scale appropriately so that all 12 notes are returned starting with the given tonic.
- For the given tonic, determine if the scale is to be returned with flats or sharps.
- Return all notes in uppercase letters (except for the `b` for flats) irrespective of the casing of the given tonic.

## Diatonic Scales

The diatonic scales, and all other scales that derive from the chromatic scale, are built upon intervals.
An interval is the space between two pitches.

The simplest interval is between two adjacent notes, and is called a "half step", or "minor second" (sometimes written as a lower-case "m").
The interval between two notes that have an interceding note is called a "whole step" or "major second" (written as an upper-case "M").
The diatonic scales are built using only these two intervals between adjacent notes.

Non-diatonic scales can contain other intervals.
An "augmented second" interval, written "A", has two interceding notes (e.g., from A to C or D♭ to E) or a "whole step" plus a "half step".
There are also smaller and larger intervals, but they will not figure into this exercise.

### Task

Given a tonic and a set of intervals, generate the musical scale starting with the tonic and following the specified interval pattern.

This is similar to generating chromatic scales except that instead of returning 12 notes, you will return N+1 notes for N intervals.
The first note is always the given tonic.
Then, for each interval in the pattern, the next note is determined by starting from the previous note and skipping the number of notes indicated by the interval.

For example, starting with G and using the seven intervals MMmMMMm, there would be the following eight notes:

| Note | Reason                                            |
| ---- | ------------------------------------------------- |
| G    | Tonic                                             |
| A    | M indicates a whole step from G, skipping G♯      |
| B    | M indicates a whole step from A, skipping A♯      |
| C    | m indicates a half step from B, skipping nothing  |
| D    | M indicates a whole step from C, skipping C♯      |
| E    | M indicates a whole step from D, skipping D♯      |
| F♯   | M indicates a whole step from E, skipping F       |
| G    | m indicates a half step from F♯, skipping nothing |

"""

FILES = {
    "scale_generator.py": 'class Scale:\n    def __init__(self, tonic):\n        pass\n\n    def chromatic(self):\n        pass\n\n    def interval(self, intervals):\n        pass\n',
    "scale_generator_test.py": '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/scale-generator/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom scale_generator import (\n    Scale,\n)\n\n\nclass ScaleGeneratorTest(unittest.TestCase):\n\n    # Test chromatic scales\n    def test_chromatic_scale_with_sharps(self):\n        expected = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]\n        self.assertEqual(Scale("C").chromatic(), expected)\n\n    def test_chromatic_scale_with_flats(self):\n        expected = ["F", "Gb", "G", "Ab", "A", "Bb", "B", "C", "Db", "D", "Eb", "E"]\n        self.assertEqual(Scale("F").chromatic(), expected)\n\n    # Test scales with specified intervals\n    def test_simple_major_scale(self):\n        expected = ["C", "D", "E", "F", "G", "A", "B", "C"]\n        self.assertEqual(Scale("C").interval("MMmMMMm"), expected)\n\n    def test_major_scale_with_sharps(self):\n        expected = ["G", "A", "B", "C", "D", "E", "F#", "G"]\n        self.assertEqual(Scale("G").interval("MMmMMMm"), expected)\n\n    def test_major_scale_with_flats(self):\n        expected = ["F", "G", "A", "Bb", "C", "D", "E", "F"]\n        self.assertEqual(Scale("F").interval("MMmMMMm"), expected)\n\n    def test_minor_scale_with_sharps(self):\n        expected = ["F#", "G#", "A", "B", "C#", "D", "E", "F#"]\n        self.assertEqual(Scale("f#").interval("MmMMmMM"), expected)\n\n    def test_minor_scale_with_flats(self):\n        expected = ["Bb", "C", "Db", "Eb", "F", "Gb", "Ab", "Bb"]\n        self.assertEqual(Scale("bb").interval("MmMMmMM"), expected)\n\n    def test_dorian_mode(self):\n        expected = ["D", "E", "F", "G", "A", "B", "C", "D"]\n        self.assertEqual(Scale("d").interval("MmMMMmM"), expected)\n\n    def test_mixolydian_mode(self):\n        expected = ["Eb", "F", "G", "Ab", "Bb", "C", "Db", "Eb"]\n        self.assertEqual(Scale("Eb").interval("MMmMMmM"), expected)\n\n    def test_lydian_mode(self):\n        expected = ["A", "B", "C#", "D#", "E", "F#", "G#", "A"]\n        self.assertEqual(Scale("a").interval("MMMmMMm"), expected)\n\n    def test_phrygian_mode(self):\n        expected = ["E", "F", "G", "A", "B", "C", "D", "E"]\n        self.assertEqual(Scale("e").interval("mMMMmMM"), expected)\n\n    def test_locrian_mode(self):\n        expected = ["G", "Ab", "Bb", "C", "Db", "Eb", "F", "G"]\n        self.assertEqual(Scale("g").interval("mMMmMMM"), expected)\n\n    def test_harmonic_minor(self):\n        expected = ["D", "E", "F", "G", "A", "Bb", "Db", "D"]\n        self.assertEqual(Scale("d").interval("MmMMmAm"), expected)\n\n    def test_octatonic(self):\n        expected = ["C", "D", "D#", "F", "F#", "G#", "A", "B", "C"]\n        self.assertEqual(Scale("C").interval("MmMmMmMm"), expected)\n\n    def test_hexatonic(self):\n        expected = ["Db", "Eb", "F", "G", "A", "B", "Db"]\n        self.assertEqual(Scale("Db").interval("MMMMMM"), expected)\n\n    def test_pentatonic(self):\n        expected = ["A", "B", "C#", "E", "F#", "A"]\n        self.assertEqual(Scale("A").interval("MMAMA"), expected)\n\n    def test_enigmatic(self):\n        expected = ["G", "G#", "B", "C#", "D#", "F", "F#", "G"]\n        self.assertEqual(Scale("G").interval("mAMMMmm"), expected)\n'
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = '# These tests are auto-generated with test data from:\n# https://github.com/exercism/problem-specifications/tree/main/exercises/scale-generator/canonical-data.json\n# File last updated on 2023-07-19\n\nimport unittest\n\nfrom scale_generator import (\n    Scale,\n)\n\n\nclass ScaleGeneratorTest(unittest.TestCase):\n\n    # Test chromatic scales\n    def test_chromatic_scale_with_sharps(self):\n        expected = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]\n        self.assertEqual(Scale("C").chromatic(), expected)\n\n    def test_chromatic_scale_with_flats(self):\n        expected = ["F", "Gb", "G", "Ab", "A", "Bb", "B", "C", "Db", "D", "Eb", "E"]\n        self.assertEqual(Scale("F").chromatic(), expected)\n\n    # Test scales with specified intervals\n    def test_simple_major_scale(self):\n        expected = ["C", "D", "E", "F", "G", "A", "B", "C"]\n        self.assertEqual(Scale("C").interval("MMmMMMm"), expected)\n\n    def test_major_scale_with_sharps(self):\n        expected = ["G", "A", "B", "C", "D", "E", "F#", "G"]\n        self.assertEqual(Scale("G").interval("MMmMMMm"), expected)\n\n    def test_major_scale_with_flats(self):\n        expected = ["F", "G", "A", "Bb", "C", "D", "E", "F"]\n        self.assertEqual(Scale("F").interval("MMmMMMm"), expected)\n\n    def test_minor_scale_with_sharps(self):\n        expected = ["F#", "G#", "A", "B", "C#", "D", "E", "F#"]\n        self.assertEqual(Scale("f#").interval("MmMMmMM"), expected)\n\n    def test_minor_scale_with_flats(self):\n        expected = ["Bb", "C", "Db", "Eb", "F", "Gb", "Ab", "Bb"]\n        self.assertEqual(Scale("bb").interval("MmMMmMM"), expected)\n\n    def test_dorian_mode(self):\n        expected = ["D", "E", "F", "G", "A", "B", "C", "D"]\n        self.assertEqual(Scale("d").interval("MmMMMmM"), expected)\n\n    def test_mixolydian_mode(self):\n        expected = ["Eb", "F", "G", "Ab", "Bb", "C", "Db", "Eb"]\n        self.assertEqual(Scale("Eb").interval("MMmMMmM"), expected)\n\n    def test_lydian_mode(self):\n        expected = ["A", "B", "C#", "D#", "E", "F#", "G#", "A"]\n        self.assertEqual(Scale("a").interval("MMMmMMm"), expected)\n\n    def test_phrygian_mode(self):\n        expected = ["E", "F", "G", "A", "B", "C", "D", "E"]\n        self.assertEqual(Scale("e").interval("mMMMmMM"), expected)\n\n    def test_locrian_mode(self):\n        expected = ["G", "Ab", "Bb", "C", "Db", "Eb", "F", "G"]\n        self.assertEqual(Scale("g").interval("mMMmMMM"), expected)\n\n    def test_harmonic_minor(self):\n        expected = ["D", "E", "F", "G", "A", "Bb", "Db", "D"]\n        self.assertEqual(Scale("d").interval("MmMMmAm"), expected)\n\n    def test_octatonic(self):\n        expected = ["C", "D", "D#", "F", "F#", "G#", "A", "B", "C"]\n        self.assertEqual(Scale("C").interval("MmMmMmMm"), expected)\n\n    def test_hexatonic(self):\n        expected = ["Db", "Eb", "F", "G", "A", "B", "Db"]\n        self.assertEqual(Scale("Db").interval("MMMMMM"), expected)\n\n    def test_pentatonic(self):\n        expected = ["A", "B", "C#", "E", "F#", "A"]\n        self.assertEqual(Scale("A").interval("MMAMA"), expected)\n\n    def test_enigmatic(self):\n        expected = ["G", "G#", "B", "C#", "D#", "F", "F#", "G"]\n        self.assertEqual(Scale("G").interval("mAMMMmm"), expected)\n'
    (workspace / "scale_generator_test.py").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "scale_generator_test.py")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
