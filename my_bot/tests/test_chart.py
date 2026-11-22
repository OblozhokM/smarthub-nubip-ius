from utils import chart, png


def test_sparkline():
    assert chart.sparkline([]) == ""
    assert chart.sparkline([5, 5, 5]) == "▄▄▄"
    assert chart.sparkline(list(range(8))) == "▁▂▃▄▅▆▇█"


def test_downsample_averages_chunks():
    points = [
        {"time": i * 1000, "value": float(i)} for i in range(1, 6)
    ]
    result = chart.downsample(points, 2)
    assert len(result) == 2
    assert result[0]["time"] == 2000.0
    assert result[0]["value"] == 2.0
    assert result[1]["value"] == 4.5


def test_downsample_keeps_short_series():
    points = [{"time": 1, "value": 1}, {"time": 2, "value": 2}]
    assert chart.downsample(points, 10) is points


def test_make_view_and_mapping():
    points = [
        {"time": 1000, "value": 10},
        {"time": 3000, "value": 20},
    ]
    plot = {"left": 70, "top": 20, "width": 550, "height": 295}
    view = chart.make_view(points, plot)
    assert view["tMin"] == 1000 and view["tMax"] == 3000
    assert view["vMin"] < 10 and view["vMax"] > 20
    assert chart.to_x(view, 1000) == 70
    assert chart.to_x(view, 3000) == 620
    assert chart.to_y(view, 20) < chart.to_y(view, 10)

    flat = chart.make_view([{"time": 5, "value": 1}], plot)
    assert chart.to_x(flat, 5) == 70


def test_build_line_chart_dimensions_and_background():
    points = [{"time": i * 60000, "value": 20 + (i % 3)} for i in range(6)]
    canvas = chart.build_line_chart(points, {"min": 15, "max": 28})
    assert canvas["width"] == 640
    assert canvas["height"] == 360
    assert canvas["pixels"][:3] == bytes(chart.WHITE)


def test_chart_to_png_signature_and_size():
    points = [{"time": i * 60000, "value": 19.0} for i in range(3)]
    data = chart.chart_to_png(points, {"min": 15, "max": 28})
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert int.from_bytes(data[16:20], "big") == 640
    assert int.from_bytes(data[20:24], "big") == 360


def test_png_canvas_helpers():
    canvas = png.create_canvas(3, 2, (255, 255, 255))
    png.fill_rect(canvas, 0, 0, 1, 1, (1, 2, 3))
    assert canvas["pixels"][:3] == bytes((1, 2, 3))
    png.set_pixel(canvas, -5, -5, (9, 9, 9))
    assert canvas["pixels"][:3] == bytes((1, 2, 3))
    assert png.text_width("12", 2) == 14
