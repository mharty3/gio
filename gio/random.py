"""
Random surfaces.

The code in this module was substantially adapted from Pierre Vigier's code at
https://github.com/pvigier/perlin-numpy

Author: Pierre Vigier
Licence: MIT

Copyright 2022 Pierre Vigier

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import numpy as np
import xarray as xr


def interpolant(t):
    """
    By Pierre Vigier https://github.com/pvigier/perlin-numpy
    Licence: MIT
    """
    return t*t*t*(t*(t*6 - 15) + 10)


def perlin_noise(shape, res,
                 rng=None,
                 tileable=(False, False),
                 interpolant=interpolant):
    """
    Generate a 2D numpy array of perlin noise.
    
    By Pierre Vigier https://github.com/pvigier/perlin-numpy
    Licence: MIT

    Args:
        shape: The shape of the generated array (tuple of two ints).
            This must be a multple of res.
        res: The number of periods of noise to generate along each
            axis (tuple of two ints). Note shape must be a multiple of
            res.
        tileable: If the noise should be tileable along each axis
            (tuple of two bools). Defaults to (False, False).
        interpolant: The interpolation function, defaults to
            t*t*t*(t*(t*6 - 15) + 10).

    Returns:
        A numpy array of shape shape with the generated noise.

    Raises:
        ValueError: If shape is not a multiple of res.
    """
    delta = (res[0] / shape[0], res[1] / shape[1])
    d = (shape[0] // res[0], shape[1] // res[1])
    grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1, 2, 0) % 1

    # Gradients.
    angles = 2 * np.pi * rng.random(size=(res[0]+1, res[1]+1))
    gradients = np.dstack((np.cos(angles), np.sin(angles)))
    if tileable[0]:
        gradients[-1, :] = gradients[0, :]
    if tileable[1]:
        gradients[:,-1] = gradients[:,0]
    gradients = gradients.repeat(d[0], 0).repeat(d[1], 1)
    g00 = gradients[    :-d[0],    :-d[1]]
    g10 = gradients[d[0]:     ,    :-d[1]]
    g01 = gradients[    :-d[0],d[1]:     ]
    g11 = gradients[d[0]:     ,d[1]:     ]

    # Ramps.
    n00 = np.sum(np.dstack((grid[:,:,0]  , grid[:,:,1]  )) * g00, 2)
    n10 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]  )) * g10, 2)
    n01 = np.sum(np.dstack((grid[:,:,0]  , grid[:,:,1]-1)) * g01, 2)
    n11 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]-1)) * g11, 2)

    # Interpolation.
    t = interpolant(grid)
    n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
    n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
    return np.sqrt(2)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)


def fractal_noise(shape,
                  res,
                  rng=None,
                  octaves=1,
                  persistence=0.5,
                  lacunarity=2,
                  tileable=(False, False),
                  interpolant=interpolant,
                  ):
    """
    Generate a 2D numpy array of fractal noise.

    By Pierre Vigier https://github.com/pvigier/perlin-numpy
    Licence: MIT

    Args:
        shape: The shape of the generated array (tuple of two ints).
            This must be a multiple of lacunarity**(octaves-1)*res.
        res: The number of periods of noise to generate along each
            axis (tuple of two ints). Note shape must be a multiple of
            (lacunarity**(octaves-1)*res).
        octaves: The number of octaves in the noise. Defaults to 1.
        persistence: The scaling factor between two octaves.
        lacunarity: The frequency factor between two octaves.
        tileable: If the noise should be tileable along each axis
            (tuple of two bools). Defaults to (False, False).
        interpolant: The, interpolation function, defaults to
            t*t*t*(t*(t*6 - 15) + 10).

    Returns:
        A numpy array of fractal noise and of shape shape generated by
        combining several octaves of perlin noise.

    Raises:
        ValueError: If shape is not a multiple of lacunarity**(octaves-1)*res.
    """
    noise = np.zeros(shape)
    f, a = 1, 1
    for _ in range(octaves):
        this_res = (f*res[0], f*res[1])
        noise += a * perlin_noise(shape,
                                  this_res,
                                  tileable=tileable,
                                  interpolant=interpolant,
                                  rng=rng
                                  )
        f *= lacunarity
        a *= persistence

    return noise


def generate_random_surface(size,
                            res=2,
                            octaves=2,
                            lacunarity=2,
                            persistence=0.5,
                            random_seed=None
                            ):
    """
    Make a square grid of **at least** the given size (length of side), with
    the given parameters. Size must be a multiple of lacunarity**(octaves-1)*res
    so the smallest possible size greater than the one provided is used.

    Args:
        size (int or tuple): minimum length of side of the grid.
        res (int or tuple): number of periods of noise to generate along
            each axis.
        octaves (int): number of octaves of noise (bandwidth).
        lacunarity (float): lacunarity of the noise (frequency factor between
            octaves). Default: 2.
        persistence (float): persistence of the noise (amplitude factor between
            octaves). Default: 0.5.
        random_seed (int): random seed.

    Returns:
        xarray.DataArray: the grid.
    """
    # `res` and `size` can be ints or tuples.
    if isinstance(res, int):
        res = (res, res)
    if isinstance(size, int):
        size = (size, size)

    # Note shape must be a multiple of (lacunarity**(octaves-1)*res).
    # Not sure what happens if res has different values for each axis.
    size0, size1 = size
    while size0 % (lacunarity**(octaves - 1) * res[0]) > 0:
        size0 += 1
        if size0 > 35_500:
            raise RuntimeError("Smallest compatible surface is >10GB.")
    while size1 % (lacunarity**(octaves - 1) * res[1]) > 0:
        size1 += 1
        if size1 > 35_500:
            raise RuntimeError("Smallest compatible surface is >10GB.")

    rng = np.random.default_rng(seed=random_seed)
    noise = fractal_noise((size0, size1),
                          res=res,
                          octaves=octaves,
                          lacunarity=lacunarity,
                          persistence=persistence,
                          rng=rng
                          )
    i, j = map(np.arange, noise.shape)
    return xr.DataArray(noise,
                        dims=('i', 'j'),
                        coords={'i': i,
                                'j': j},
                        attrs={'source': 'gio.random',})
