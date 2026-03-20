import os
import warnings
import streamlit.components.v1 as components
from PIL import Image
from typing import Literal, Optional, Tuple
import numpy as np
import io
import base64

_RELEASE = True
_UNSET = object()  # sentinel for detecting explicit should_resize_image usage

if not _RELEASE:
    _component_func = components.declare_component(
        "st_cropper",
        url="http://localhost:3000",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component("st_cropper", path=build_dir)


def _resize_img(img: Image, max_height: int = 700, max_width: int = 700,
                target_width: Optional[int] = None, target_height: Optional[int] = None) -> Image:
    """Resize the image for display, maintaining aspect ratio.

    If target_width is set, resize to that exact width.
    If target_height is set, resize to that exact height.
    Otherwise, cap at max_height x max_width (legacy behavior).
    """
    if target_width is not None and target_width < img.width:
        ratio = target_width / img.width
        img = img.resize((target_width, int(img.height * ratio)))
    elif target_height is not None and target_height < img.height:
        ratio = target_height / img.height
        img = img.resize((int(img.width * ratio), target_height))
    else:
        if img.height > max_height:
            ratio = max_height / img.height
            img = img.resize((int(img.width * ratio), int(img.height * ratio)))
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    return img


def _recommended_box(img: Image, aspect_ratio: tuple = None) -> dict:
    # Find a recommended box for the image (could be replaced with image detection)
    box = (img.width * 0.2, img.height * 0.2, img.width * 0.8, img.height * 0.8)
    box = [int(i) for i in box]
    height = box[3] - box[1]
    width = box[2] - box[0]

    # If an aspect_ratio is provided, then fix the aspect
    if aspect_ratio:
        ideal_aspect = aspect_ratio[0] / aspect_ratio[1]
        height = (box[3] - box[1])
        current_aspect = width / height
        if current_aspect > ideal_aspect:
            new_width = int(ideal_aspect * height)
            offset = (width - new_width) // 2
            resize = (offset, 0, -offset, 0)
        else:
            new_height = int(width / ideal_aspect)
            offset = (height - new_height) // 2
            resize = (0, offset, 0, -offset)
        box = [box[i] + resize[i] for i in range(4)]
        left = box[0]
        top = box[1]
        width = 0
        iters = 0
        while width < box[2] - left:
            width += aspect_ratio[0]
            iters += 1
        height = iters * aspect_ratio[1]
    else:
        left = box[0]
        top = box[1]
        width = box[2] - box[0]
        height = box[3] - box[1]
    return {'left': int(left), 'top': int(top), 'width': int(width), 'height': int(height)}

def _get_cropped_image(img_file:Image, was_resized:bool, orig_file: Image, rect: dict):
    # Return a cropped image. Use original if image was resized (coords already scaled back).
    source = orig_file if was_resized else img_file
    cropped_img = source.crop(
            (rect['left'], rect['top'], rect['width'] + rect['left'], rect['height'] + rect['top']))
    return cropped_img

def st_cropper(img_file: Image, realtime_update: bool = True, default_coords: Optional[tuple] = None, box_color: str = 'blue', aspect_ratio: tuple = None,
               return_type: str = 'image', box_algorithm=None, key=None, should_resize_image = _UNSET, stroke_width = 3,
               display_width: Optional[int] = None, display_height: Optional[int] = None,
               width: Literal['stretch', 'content'] = 'content') -> Image.Image | dict | tuple[Image.Image, dict]:
    """Create a new instance of "st_cropper".

    Parameters
    ----------
    img_file: PIL.Image
        The image to be cropped
    realtime_update: bool
        A boolean value to determine whether the cropper will update in realtime.
        If set to False, a double click is required to crop the image.
    default_coords: Optional[tuple]
        The (xl, xr, yt, yb) coords to use by default
    box_color: string
        The color of the cropper's bounding box. Defaults to blue, can accept
        other string colors recognized by fabric.js or hex colors in a format like
        '#ff003c'
    aspect_ratio: tuple
        Tuple representing the ideal aspect ratio: e.g. 1:1 aspect is (1,1) and 4:3 is (4,3)
    box_algorithm: function
        A function that can return a bounding box, the function should accept a PIL image
        and return a dictionary with keys: 'left', 'top', 'width', 'height'. Note that
        if you use a box_algorithm with an aspect_ratio, you will need to decide how to
        handle the aspect_ratio yourself
    return_type: str
        The return type that you would like. The default, 'image', returns the cropped
        image, while 'box' returns a dictionary identifying the box by its
        left and top coordinates as well as its width and height. Alternatively 'both'
        will return both the cropped image and box coordinates
    key: str or None
        An optional key that uniquely identifies this component. If this is
        None, and the component's arguments are changed, the component will
        be re-mounted in the Streamlit frontend and lose its current state.
    should_resize_image: bool
        Deprecated. Use display_width or display_height instead.
    stroke_width: int
        The width of the bounding box
    display_width: int or None
        The width in pixels for the displayed image. Maintains aspect ratio.
        Cannot be used together with display_height.
    display_height: int or None
        The height in pixels for the displayed image. Maintains aspect ratio.
        Cannot be used together with display_width.
    width: 'stretch' or 'content'
        The width mode of the widget container. 'content' (default) displays
        at the image's natural size, capped at the container width. 'stretch'
        fills the available column width.

    Returns
    -------
    PIL.Image
    The cropped image in PIL.Image format
    or
    Dict of box with coordinates
    or
    Tuple of PIL.Image and box coordinates
    """

    # Validate parameters
    if display_width is not None and display_height is not None:
        raise ValueError("Cannot specify both display_width and display_height. Choose one to maintain aspect ratio.")

    # Handle deprecated should_resize_image parameter
    if should_resize_image is not _UNSET:
        warnings.warn(
            "should_resize_image is deprecated. Use display_width or display_height instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        should_resize_image = bool(should_resize_image)
    else:
        should_resize_image = True  # default behavior

    # Ensure that the return type is in the list of supported return types
    supported_types = ('image', 'box', 'both')
    if return_type.lower() not in supported_types:
        raise ValueError(f"{return_type} is not a supported value for return_type, try one of {supported_types}")

    resized_ratio_w = 1
    resized_ratio_h = 1
    orig_file = img_file.copy()

    # Handle image resizing
    if display_width is not None or display_height is not None:
        img_file = _resize_img(img_file, target_width=display_width, target_height=display_height)
        resized_ratio_w = orig_file.width / img_file.width
        resized_ratio_h = orig_file.height / img_file.height
    elif should_resize_image:
        img_file = _resize_img(img_file)
        resized_ratio_w = orig_file.width / img_file.width
        resized_ratio_h = orig_file.height / img_file.height

    if default_coords is not None:
        box = {'left': default_coords[0] // resized_ratio_w,
               'top': default_coords[2] // resized_ratio_h,
               'width': (default_coords[1] - default_coords[0]) // resized_ratio_w,
               'height': (default_coords[3] - default_coords[2]) // resized_ratio_h
              }
    else:
        # Find a default box
        if not box_algorithm:
            box = _recommended_box(img_file, aspect_ratio=aspect_ratio)
        else:
            box = box_algorithm(img_file, aspect_ratio=aspect_ratio)

    rect_left = box['left']
    rect_top = box['top']
    rect_width = box['width']
    rect_height = box['height']

    # Get arguments to send to frontend
    canvas_width = img_file.width
    canvas_height = img_file.height
    lock_aspect = False
    if aspect_ratio:
        lock_aspect = True


    # Convert image to base64 string for passing to Javascript
    buffered = io.BytesIO()
    img_file.convert("RGBA").save(buffered, format="PNG")
    image_data = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

    # Call through to our private component function. Arguments we pass here
    # will be sent to the frontend, where they'll be available in an "args"
    # dictionary.
    #
    # Defaults to a box whose vertices are at 20% and 80% of height and width.
    # The _recommended_box function could be replaced with some kind of image
    # detection algorith if it suits your needs.
    component_value = _component_func(canvasWidth=canvas_width, canvasHeight=canvas_height,
                                      realtimeUpdate=realtime_update, strokeWidth=stroke_width,
                                      rectHeight=rect_height, rectWidth=rect_width, rectLeft=rect_left, rectTop=rect_top,
                                      boxColor=box_color, imageData=image_data, lockAspect=lock_aspect,
                                      widthMode=width, key=key)

    # Return a cropped image using the box from the frontend
    if component_value:
        rect = component_value['coords']
    else:
        rect = box

    # Scale box according to the resize ratio, but make sure new box does not exceed original bounds
    if resized_ratio_w != 1 or resized_ratio_h != 1:
        rect['left'] = max(0, int(rect['left'] * resized_ratio_w))
        rect['top'] = max(0, int(rect['top'] * resized_ratio_h))
        rect['width'] = min(orig_file.size[0] - rect['left'], int(rect['width'] * resized_ratio_w))
        rect['height'] = min(orig_file.size[1] - rect['top'], int(rect['height'] * resized_ratio_h))

    # Return the value desired by the return_type
    was_resized = resized_ratio_w != 1 or resized_ratio_h != 1
    if return_type.lower() == 'image':
        return _get_cropped_image(img_file, was_resized, orig_file, rect)
    elif return_type.lower() == 'box':
        return rect
    elif return_type.lower() == 'both':
        return _get_cropped_image(img_file, was_resized, orig_file, rect), rect


# Add some test code to play with the component while it's in development.
# During development, we can run this just as we would any other Streamlit
# app: `$ streamlit run my_component/__init__.py`
if not _RELEASE:
    import streamlit as st

    # Upload an image and set some options for demo purposes
    st.header("Cropper Testing")
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

    return_type_choice = st.sidebar.radio(label="Return type", options=["Cropped image", "Rect coords"])
    return_type_dict = {
        "Cropped image": "image",
        "Rect coords": "box"
    }
    return_type = return_type_dict[return_type_choice]

    # New sizing options
    width_mode: Literal['stretch', 'content'] = st.sidebar.radio(label="Widget Width", options=["stretch", "content"])  # type: ignore[assignment]
    size_mode = st.sidebar.radio(label="Display Size", options=["Default", "Custom Width", "Custom Height"])
    display_width = None
    display_height = None
    if size_mode == "Custom Width":
        display_width = st.sidebar.slider("Display Width (px)", 100, 1200, 500)
    elif size_mode == "Custom Height":
        display_height = st.sidebar.slider("Display Height (px)", 100, 1200, 400)

    if img_file:
        img = Image.open(img_file)

        if return_type == 'box':
            rect = st_cropper(
                img_file=img,
                realtime_update=True,
                box_color=box_color,
                aspect_ratio=aspect_ratio,
                return_type=return_type,
                width=width_mode,
                display_width=display_width,
                display_height=display_height,
                )
            raw_image = np.asarray(img).astype('uint8')
            left, top, width, height = tuple(map(int, rect.values()))
            st.write(rect)
            masked_image = np.zeros(raw_image.shape, dtype='uint8')
            masked_image[top:top + height, left:left + width] = raw_image[top:top + height, left:left + width]
            st.image(Image.fromarray(masked_image), caption='masked image')
        else:
            if not realtime_update:
                st.write("Double click to save crop")
            # Get a cropped image from the frontend
            cropped_img = st_cropper(
                img_file=img,
                realtime_update=realtime_update,
                box_color=box_color,
                aspect_ratio=aspect_ratio,
                return_type=return_type,
                width=width_mode,
                display_width=display_width,
                display_height=display_height,
            )

            # Manipulate cropped image at will
            st.write("Preview")
            _ = cropped_img.thumbnail((150, 150))
            st.image(cropped_img)
