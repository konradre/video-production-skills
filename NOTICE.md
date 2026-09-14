# Third-party notices

The film looks in `look-library/` (`film-*.cube`) were baked from spectral negative x print base cubes taken
from ComfyUI-Darkroom, which vendors the spectral_film_lut baker. Both are MIT licensed; their notices
follow, as the MIT licence requires for the portions incorporated in the derived cubes. Nothing else in
this repository vendors third-party code; the tools call Topaz Video AI, DaVinci Resolve and the
Dehancer plugin through their own interfaces, and the designed elements render with HyperFrames
(Apache-2.0) fetched at render time.

## ComfyUI-Darkroom — https://github.com/jeremieLouvaert/ComfyUI-Darkroom

Copyright (c) the ComfyUI-Darkroom author (jeremieLouvaert). The project declares the MIT licence in its
package metadata (`pyproject.toml`, `license = { file = "LICENSE" }`); the licence file itself was not
present in the repository when this notice was written (September 2026), so the MIT text below is
reproduced on the strength of that declaration. The spectral base cubes were baked by its vendored
spectral_film_lut engine from published film datasheets.

## spectral_film_lut — https://github.com/JanLohse/spectral_film_lut

Copyright (c) 2026 Jan Lohse

## MIT licence text (applies to both)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Dehancer

The `look-library/drx/*.drx` files are DaVinci Resolve grade files holding this repository's own node
settings, including the parameter values of the Dehancer Pro OFX plugin. They contain no Dehancer film
profile data; applying them needs a licensed Dehancer Pro 7.x install with its profiles downloaded.
Cubes exported by Dehancer's own LUT Generator are licensee-only and are not, and must never be,
published here.
