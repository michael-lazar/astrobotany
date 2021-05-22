from __future__ import annotations

import subprocess
import typing
from typing import List

from midiutil import MIDIFile

if typing.TYPE_CHECKING:
    from models import Song


class Synthesizer:

    # Use stdin/stdout and generate mono OGG Vorbis
    midi_command = ["timidity", "-", "-OvM", "-o", "-"]
    midi_notes = {
        "G₃": 55,
        "A₃": 57,
        "B₃": 59,
        "C₄": 60,
        "D₄": 62,
        "E₄": 64,
        "F₄": 65,
        "G₄": 67,
        "A₄": 69,
        "B₄": 71,
        "C₅": 72,
        "D₅": 74,
        "E₅": 76,
    }

    tab_string = "||{}{}{}{}|{}{}{}{}|{}{}{}{}|{}{}{}{}||"
    note_char_map = [
        ".",  # Rest
        "—",  # Hold previous note
    ] + list(midi_notes.keys())

    def __init__(self, song_map: List[str], bpm):
        self.song_map = song_map
        self.bpm = bpm

    @classmethod
    def from_song(cls, song: Song) -> Synthesizer:
        data = song.get_data()
        return cls(data["notes"], data["tempo"])

    def build_midi_file(self) -> MIDIFile:
        # Compress runs of the same note
        reduced_song_map = [[self.song_map[0], 1]]  # [(note, duration), ...]
        for note in self.song_map[1:]:
            if note == "-":
                reduced_song_map[-1][1] += 1
            else:
                reduced_song_map.append([note, 1])

        midi = MIDIFile()
        midi.addTempo(0, 0, self.bpm)
        midi.addProgramChange(0, 0, 0, 7)

        offset = 0
        for note, count in reduced_song_map:
            if note not in (".", "—"):
                pitch = self.midi_notes[note]
                duration = count - 0.5
                midi.addNote(0, 0, pitch, offset, duration, 127)
            offset += count

        return midi

    def get_raw_data(self) -> bytes:
        midi = self.build_midi_file()
        proc = subprocess.Popen(self.midi_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        midi.writeFile(proc.stdin)
        data, _ = proc.communicate(timeout=5)
        return data

    def get_tab(self) -> str:
        display_chars = (f" {x:<2}" for x in self.song_map)
        return self.tab_string.format(*display_chars)
