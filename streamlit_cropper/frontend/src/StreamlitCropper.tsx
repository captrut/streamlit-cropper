import React, {useEffect, useRef, useState} from 'react';
import {ComponentProps, Streamlit, withStreamlitConnection} from "./streamlit";
import { Canvas, Rect, Image as FabricImage } from 'fabric';

interface PythonArgs {
    canvasWidth: number
    canvasHeight: number
    rectTop: number
    rectLeft: number
    rectWidth: number
    rectHeight: number
    realtimeUpdate: boolean
    boxColor: string
    strokeWidth: number
    imageData: string // base64 string
    lockAspect: boolean
    widthMode: string // 'stretch' | 'content'
}

const applyStretchMode = (fabricCanvas: Canvas, canvasWidth: number, canvasHeight: number, containerWidth: number) => {
    const scaleFactor = containerWidth / canvasWidth;
    fabricCanvas.setDimensions(
        { width: `${containerWidth}px`, height: `${canvasHeight * scaleFactor}px` },
        { cssOnly: true }
    );
    fabricCanvas.setZoom(scaleFactor);
    Streamlit.setFrameHeight(Math.ceil(canvasHeight * scaleFactor));
};

const StreamlitCropper = (props: ComponentProps) => {
    const [canvas, setCanvas] = useState<Canvas | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const rectRef = useRef<Rect | null>(null);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [containerWidth, setContainerWidth] = useState<number | null>(null);
    const {canvasWidth, canvasHeight, imageData, widthMode}: PythonArgs = props.args;
    // imageData is now a base64 string (data URL)
    const dataUri = imageData || "";

    // Measure actual container width via ResizeObserver
    useEffect(() => {
        if (!containerRef.current) return;
        const ro = new ResizeObserver((entries) => {
            const width = entries[0].contentRect.width;
            if (width > 0) setContainerWidth(width);
        });
        ro.observe(containerRef.current);
        return () => ro.disconnect();
    }, []);

    /**
     * Initialize canvas on mount and add a rectangle
     */
    useEffect(() => {
        // Only initialize Fabric once
        if (!canvasRef.current || canvas) return;
        const {rectTop, rectLeft, rectWidth, rectHeight, boxColor, strokeWidth, lockAspect}: PythonArgs = props.args;
        const fabricCanvas = new Canvas(canvasRef.current, {
            enableRetinaScaling: false,
            uniformScaling: lockAspect
        });

        if (dataUri) {
            FabricImage.fromURL(dataUri).then((img: FabricImage) => {
                fabricCanvas.backgroundImage = img;
                fabricCanvas.requestRenderAll();
            });
        }

        const rect = new Rect({
            left: rectLeft,
            top: rectTop,
            fill: '',
            width: rectWidth,
            height: rectHeight,
            objectCaching: true,
            stroke: boxColor,
            strokeWidth: strokeWidth,
        });
        rect.set({
            hasRotatingControl: false,
        });
        rect.setControlsVisibility && rect.setControlsVisibility({
            mt: !lockAspect,
            mb: !lockAspect,
            ml: !lockAspect,
            mr: !lockAspect,
            mtr: false,
            tl: true,
            tr: true,
            bl: true,
            br: true
        });
        fabricCanvas.add(rect);
        rectRef.current = rect;

        // Initial frame height — will be corrected by the containerWidth useEffect
        // once the container is measured.
        Streamlit.setFrameHeight();

        setCanvas(fabricCanvas);

        return () => {
            fabricCanvas.dispose();
        };
        // eslint-disable-next-line
    }, []);

    // Handle width mode — apply when containerWidth is measured or changes
    useEffect(() => {
        if (!canvas || !containerWidth) return;

        if (widthMode === 'stretch') {
            // Always fill the container width
            applyStretchMode(canvas, canvasWidth, canvasHeight, containerWidth);
        } else {
            // Content mode: display at natural size, but cap at container width
            if (canvasWidth > containerWidth) {
                applyStretchMode(canvas, canvasWidth, canvasHeight, containerWidth);
            } else {
                // Reset to natural size (undo any previous scaling)
                canvas.setDimensions(
                    { width: `${canvasWidth}px`, height: `${canvasHeight}px` },
                    { cssOnly: true }
                );
                canvas.setZoom(1);
                Streamlit.setFrameHeight(canvasHeight);
            }
        }
        canvas.requestRenderAll();
    }, [containerWidth, canvas, widthMode, canvasWidth, canvasHeight]);

    // Update rectangle properties when props.args change
    useEffect(() => {
        if (!canvas || !rectRef.current) return;
        const {rectTop, rectLeft, rectWidth, rectHeight, boxColor, strokeWidth, lockAspect}: PythonArgs = props.args;
        const rect = rectRef.current;
        rect.set({
            left: rectLeft,
            top: rectTop,
            width: rectWidth,
            height: rectHeight,
            stroke: boxColor,
            strokeWidth: strokeWidth,
            hasRotatingControl: false,
        });
        rect.setControlsVisibility && rect.setControlsVisibility({
            mt: !lockAspect,
            mb: !lockAspect,
            ml: !lockAspect,
            mr: !lockAspect,
            mtr: false,
            tl: true,
            tr: true,
            bl: true,
            br: true
        });
        rect.setCoords();
        canvas.requestRenderAll();
    }, [props.args, canvas]);


    /**
     * On update (either realtime or doubleclick), send the coordinates of the rectangle
     * back to streamlit.
     */
    useEffect(() => {
        const {realtimeUpdate}: PythonArgs = props.args
        if (!canvas) {
            return;
        }
        const handleEvent = () => {
            canvas.renderAll()
            const coords = canvas.getObjects()[0].getBoundingRect()
            Streamlit.setComponentValue({coords:coords})
        }

        if (realtimeUpdate) {
        canvas.on("object:modified", handleEvent)
        return () => {
            canvas.off("object:modified");
        }
        }
        else {
        canvas.on("mouse:dblclick", handleEvent)
        return () => {
            canvas.off("mouse:dblclick");
        }
        }
    })

    return (
        <div ref={containerRef} style={{ width: '100%' }}>
            <canvas ref={canvasRef} width={canvasWidth} height={canvasHeight}/>
        </div>
    )
};

export default withStreamlitConnection(StreamlitCropper);
