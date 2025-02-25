"""
MIT License

Copyright (c) 2021-present Defxult#8269

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.
"""

from io import BufferedIOBase, BytesIO, IOBase
from os import PathLike
from pathlib import Path
from typing import Optional, Union

from aiohttp import ClientSession
from PIL import Image, ImageDraw, ImageFont

from .errors import InvalidImageType, InvalidImageUrl


class Settings:
    """
    Represents the settings for the rank card

    Parameters
    ----------
    background: :class:`Union[PathLike, BufferedIOBase, str]`
        The background image for the rank card. This can be a path to a file or a file-like object in `rb` mode or URL

    bar_color: :class:`str`
        The color of the XP bar. This can be a string hex code or a color name. Default is `white`
    
    text_color: :class:`str`
        The color of the text. This can be a string hex code or a color name. Default is `white`

    Attributes
    ----------
    - `background`
    - `bar_color`
    - `text_color`
    """

    __slots__ = ('background', 'bar_color', 'text_color')

    def __init__(
        self,
        background: Union[PathLike, BufferedIOBase, str],
        bar_color: str = 'white',
        text_color: str = 'white'
    ) -> None:
        self.background = background
        self.bar_color = bar_color
        self.text_color = text_color
    
    def to_dict(self) -> dict:
        return {key : getattr(self, key) for key in self.__class__.__slots__}


class RankCard:
    """Represents the users rank card

    Parameters
    ----------
    settings: :class:`Settings`
        The settings for the rank card
    
    avatar: :class:`str`
        The avatar image for the rank card. This can only be a URL to an image
    
    level: :class:`int`
        The level of the member
    
    username: :class:`str`
        The username of the member
    
    current_xp: :class:`int`
        The current amount of XP the member has
    
    max_xp: :class:`int`
        The amount of XP required for the member to level up
            
    Attributes
    ----------
    - `avatar`
    - `level`
    - `username`
    - `current_xp`
    - `max_xp`    
    - `background`
    - `bar_color`
    - `text_color`

    Raises
    ------
    - `InvalidImageType`
        If the image type is not supported
    - `InvalidImageUrl`
        If the image url is invalid
    """

    __slots__ = ('settings', 'avatar', 'level', 'username', 'current_xp', 'max_xp', 'background', 'bar_color', 'text_color')

    def __init__(
        self,
        settings:Settings,
        avatar:str,
        level:int,
        username:str,
        current_xp:int,
        max_xp:int
    )-> None:
        self.background = settings.background
        self.bar_color = settings.bar_color
        self.text_color = settings.text_color
        self.avatar = avatar
        self.level = level
        self.username = username
        self.current_xp = current_xp
        self.max_xp = max_xp

    @staticmethod
    def _convert_number(number: int) -> str:
        if number >= 1000000:
            return f"{number / 1000000:.3f}M"
        elif number >= 1000:
            return f"{number / 1000:.3f}K"
        else:
            return str(number)

    @staticmethod
    async def _image(url:str):
        async with ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise InvalidImageUrl(f"Invalid image url: {url}")
                data = await response.read()
                return Image.open(BytesIO(data))

    async def create(self)-> Optional[BytesIO]:
        """
        Creates the rank card

        Returns
        -------
        :class:`BytesIO`
            The rank card as BytesIO

        Raises
        ------
        - :class:`InvalidImageType`
            The image type is not supported
        - :class:`InvalidImageUrl`
            The image url is invalid
        """

        path = str(Path(__file__).parent)

        if isinstance(self.background, IOBase):
            if not (self.background.seekable() and self.background.readable() and self.background.mode == "rb"):
                raise InvalidImageType(f"File buffer {self.background!r} must be seekable and readable and in binary mode")
            self.background = Image.open(self.background)
        elif isinstance(self.background, str):
            if self.background.startswith("http"):
                self.background = await RankCard._image(self.background)
            else:
                self.background = Image.open(open(self.background, "rb"))
        else:
            raise InvalidImageType(f"background must be a path or url or a file buffer, not {type(self.background)}") 

        if isinstance(self.avatar, str):
            if self.avatar.startswith("http"):
                self.avatar = await RankCard._image(self.avatar)
            else:
                self.avatar = Image.open(open(self.avatar, "rb"))
        else:
            raise InvalidImageType(f"avatar must be a url, not {type(self.avatar)}") 

        self.avatar = self.avatar.resize((170,170))

        overlay = Image.open(path + "/assets/overlay1.png")
        background = Image.new("RGBA", overlay.size)
        backgroundover = self.background.resize((638,159))
        background.paste(backgroundover,(0,0))
        
        self.background = background.resize(overlay.size)
        self.background.paste(overlay,(0,0),overlay)

        card_font = ImageFont.truetype(path + "/assets/levelfont.otf",40)
        draw = ImageDraw.Draw(self.background)

        draw.text((205,(327/2)+20), self.username,font=card_font, fill=self.text_color,stroke_width=1,stroke_fill=(0, 0, 0))
        bar_exp = (self.current_xp/self.max_xp)*420
        if bar_exp <= 50:
            bar_exp = 50    

        current_xp = RankCard._convert_number(self.current_xp)
        
        max_xp = RankCard._convert_number(self.max_xp)
        

        card_font = ImageFont.truetype(path + "/assets/levelfont.otf",30)
        draw.text((197,(327/2)+125), f"LEVEL - {RankCard._convert_number(self.level)}",font=card_font, fill=self.text_color,stroke_width=1,stroke_fill=(0, 0, 0))

        w,_ = draw.textsize(f"{current_xp}/{max_xp}", font=card_font)
        draw.text((638-w-50,(327/2)+125), f"{current_xp}/{max_xp}",font=card_font, fill=self.text_color,stroke_width=1,stroke_fill=(0, 0, 0))

        mask_im = Image.open(path + "/assets/mask_circle.jpg").convert('L').resize((170,170))
        new = Image.new("RGB", self.avatar.size, (0, 0, 0))
        try:
            new.paste(self.avatar, mask=self.avatar.convert("RGBA").split()[3])
        except Exception as e:
            print(e)
            new.paste(self.avatar, (0,0))
        self.background.paste(new, (13, 65), mask_im)

        im = Image.new("RGB", (490, 51), (0, 0, 0))
        draw = ImageDraw.Draw(im, "RGBA")
        draw.rounded_rectangle((0, 0, 420, 50), 30, fill=(255,255,255,50))
        draw.rounded_rectangle((0, 0, bar_exp, 50), 30, fill=self.bar_color)
        self.background.paste(im, (190, 235))
        new = Image.new("RGBA", self.background.size)
        new.paste(self.background,(0, 0), Image.open(path + "/assets/curvedoverlay.png").convert("L"))
        self.background = new.resize((505, 259))

        image = BytesIO()
        self.background.save(image, 'PNG')
        image.seek(0)
        return image