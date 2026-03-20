# Streamlit - Cropper

A streamlit custom component for easy image cropping

![](./demo.gif)

## Installation

```shell script
pip install streamlit-cropper
```

## Example Usage

```python
import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image

# Upload an image and set some options for demo purposes
st.header("Cropper Demo")
img_file = st.sidebar.file_uploader(label='Upload a file', type=['png', 'jpg'])
realtime_update = st.sidebar.checkbox(label="Update in Real Time", value=True)
box_color = st.sidebar.color_picker(label="Box Color", value='#0000FF')
aspect_choice = st.sidebar.radio(label="Aspect Ratio", options=["1:1", "16:9", "4:3", "2:3", "Free"])
aspect_dict = {
    "1:1": (1, 1),
    "16:9": (16, 9),
    "4:3": (4, 3),
    "2:3": (2, 3),
    "Free": None
}
aspect_ratio = aspect_dict[aspect_choice]

if img_file:
    img = Image.open(img_file)
    if not realtime_update:
        st.write("Double click to save crop")
    # Get a cropped image from the frontend
    cropped_img = st_cropper(img, realtime_update=realtime_update, box_color=box_color,
                                aspect_ratio=aspect_ratio)

    # Manipulate cropped image at will
    st.write("Preview")
    _ = cropped_img.thumbnail((150,150))
    st.image(cropped_img)
```

## Display Sizing

You can control the displayed image size using `display_width` or `display_height` (not both). The original image is always preserved at full resolution — these parameters only affect the interactive display. Images are never upscaled.

```python
# Display the image at 500px wide (maintains aspect ratio)
cropped_img = st_cropper(img, display_width=500)

# Or display at 300px tall
cropped_img = st_cropper(img, display_height=300)
```

## Widget Width

Control how the widget fills its container using the `width` parameter, similar to `st.image`:

- `'content'` (default) — displays at the image's natural size, capped at the container width
- `'stretch'` — fills the available container/column width

```python
# Fill the full column width
cropped_img = st_cropper(img, width='stretch')

# Wrap to the image's natural size
cropped_img = st_cropper(img, width='content')
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `img_file` | `PIL.Image` | required | The image to be cropped |
| `realtime_update` | `bool` | `True` | Update crop in realtime. If `False`, double click to crop. |
| `default_coords` | `tuple` | `None` | Default `(xl, xr, yt, yb)` coordinates |
| `box_color` | `str` | `'blue'` | Bounding box color (any fabric.js color or hex like `'#ff003c'`) |
| `aspect_ratio` | `tuple` | `None` | Aspect ratio as `(w, h)`, e.g. `(16, 9)` |
| `return_type` | `str` | `'image'` | `'image'`, `'box'`, or `'both'` |
| `box_algorithm` | `function` | `None` | Custom function returning `{'left', 'top', 'width', 'height'}` |
| `key` | `str` | `None` | Unique component key |
| `stroke_width` | `int` | `3` | Bounding box stroke width |
| `display_width` | `int` | `None` | Display width in pixels (maintains aspect ratio) |
| `display_height` | `int` | `None` | Display height in pixels (maintains aspect ratio) |
| `width` | `'stretch'` or `'content'` | `'content'` | Widget container width mode |

## References

- [streamlit-drawable-canvas](https://github.com/andfanilo/streamlit-drawable-canvas)

## Acknowledgments

Big thanks to zoncrd and yanirs for their contributions