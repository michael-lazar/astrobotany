from __future__ import annotations

import io
import typing
from functools import lru_cache
from typing import Iterable, List

from pydub import AudioSegment
from pydub.generators import Square

if typing.TYPE_CHECKING:
    from models import Song


class Synthesizer:

    # MIDI note numbers for C major scale, starting at G3
    scale = [55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76]

    duration = 250  # ms, length for each note

    silent_segment = AudioSegment.silent(duration=duration)

    tab_string = "||{}{}{}{}|{}{}{}{}|{}{}{}{}|{}{}{}{}||"
    note_char_map = [
        " . ",  # Rest
        " — ",  # Hold previous note
        " G₃",
        " A₃",
        " B₃",
        " C₄",
        " D₄",
        " E₄",
        " F₄",
        " G₄",
        " A₄",
        " B₄",
        " C₅",
        " D₅",
        " E₅",
    ]

    def __init__(self, song_map: List[int]):
        self.song_map = song_map

    @classmethod
    def from_song(cls, song: Song) -> Synthesizer:
        return cls(song.get_data()["notes"])

    @classmethod
    @lru_cache(400)
    def compile_note(cls, midi_number: int, count: int) -> AudioSegment:
        # http://en.wikipedia.org/wiki/MIDI_Tuning_Standard#Frequency_values
        # https://gist.github.com/jiaaro/339df443b005e12d6c2a
        frequency = (2.0 ** ((midi_number - 69) / 12.0)) * 440
        waveform = Square(frequency, duty_cycle=0.5)
        segment = waveform.to_audio_segment(duration=cls.duration * count, volume=-20)
        segment = segment.fade_in(40).fade_out(100)
        return segment

    def play_audio(self) -> Iterable[AudioSegment]:
        # Compress runs of the same note
        reduced_song_map = [[self.song_map[0], 1]]
        for note in self.song_map[1:]:
            if note == 1:
                reduced_song_map[-1][1] += 1
            else:
                reduced_song_map.append([note, 1])

        for note, count in reduced_song_map:
            if note <= 1:
                yield self.silent_segment * count
            else:
                yield self.compile_note(midi_number=self.scale[note - 2], count=count)

    def get_raw_data(self) -> bytes:
        fp = io.BytesIO()
        raw_data = sum(self.play_audio())
        raw_data.export(fp, format="mp3")
        return fp.getvalue()

    @property
    def note_chars(self) -> List[str]:
        return [self.note_char_map[n] for n in self.song_map]

    def get_tab(self) -> str:
        return self.tab_string.format(*self.note_chars)
