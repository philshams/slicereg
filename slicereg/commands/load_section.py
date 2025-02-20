from dataclasses import dataclass, field
from pathlib import Path

from slicereg.commands.base import BaseSectionRepo
from slicereg.commands.utils import Signal
from slicereg.io.tifffile import OmeTiffImageReader, TiffImageReader
from slicereg.models.image_transform import ImageTransformer
from slicereg.models.physical_transform import PhysicalTransformer
from slicereg.models.registration import Registration
from slicereg.models.section import Section
from slicereg.repos.atlas_repo import AtlasRepo


@dataclass
class LoadImageCommand:
    _repo: BaseSectionRepo
    _atlas_repo: AtlasRepo
    _ome_reader: OmeTiffImageReader
    _tiff_reader: TiffImageReader
    section_loaded: Signal = field(default_factory=Signal)

    def __call__(self, filename: str) -> None:
        filepath = Path(filename)
        atlas = self._atlas_repo.get_atlas()
        if not atlas:
            return

        cx, cy, cz = atlas.center

        if '.ome' in filepath.suffixes:
            image = self._ome_reader.read(filename=str(filepath))
        elif filepath.suffix.lower() in ['.tiff', '.tif']:
            image = self._tiff_reader.read(filename=str(filepath), resolution_um = 10)
        else:
            raise ValueError(f"{filepath.suffix} not supported")


        image = image.resample(resolution_um=10)
        section = Section(
            image=image,
            image_transform=ImageTransformer(i_shift=-0.5, j_shift=-0.5),
            physical_transform=PhysicalTransformer(x=cx, y=cy, z=cz)
        )

        registration = Registration(section=section, atlas=atlas)

        self._repo.save_section(section=section)
        self.section_loaded.emit(
            image=section.image.channels[0],
            transform=registration.image_to_volume_transform,
            resolution_um=image.resolution_um,
            atlas_image=registration.slice_atlas().channels[0]
        )
