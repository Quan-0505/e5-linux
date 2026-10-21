"""Program a legal PIXELPLL rate for PB8's own 16 MHz ILI9488 mode.

The factory display module selects PIXELPLL/16 and requests 16 MHz, but the
boot PLL is only 264.576 MHz: its /16 parent cannot produce the requested DPI
rate with an integer divider. The UMS9621 DPI divider is three bits (/1..8).
2.048 GHz -> /16 -> /8 supplies exactly the factory mode's 16 MHz and lies
within this PLL's 1.6..3.2 GHz operating range. Keep this in the PB8 profile;
neither another panel's timings nor the DSI PHY clock are changed.
"""
from pathlib import Path


def apply(kernel):
    path = Path(kernel) / 'drivers/unisoc_platform/sprd_disp/qogirn6lite/global_dpu.c'
    text = path.read_text()
    marker = '/* PB8 low-pixel-clock PLL setup: /16 parent, /8 DPI. */'
    if marker in text:
        return
    anchor = '\t\tclk_pixelpll_div = calc_div_of_pixelpll(ctx->vm.pixelclock);'
    if text.count(anchor) != 1:
        raise ValueError('Unexpected UMS9621 display clock source')
    addition = '''

\t\t/* PB8 low-pixel-clock PLL setup: /16 parent, /8 DPI. */
\t\tif (of_node_name_eq(panel->info.of_node,
\t\t\t\t"lcd_ili9488_easyquick_mipi_fhd") &&
\t\t    ctx->vm.pixelclock == 16000000 && clk_pixelpll_div == 16) {
\t\t\t/* The DPI composite does not propagate rate changes to its
\t\t\t * PLL. Keep the VCO within 1.6..3.2 GHz before selecting DPI.
\t\t\t */
\t\t\tret = clk_set_rate(clk_ctx->clk_dpi_pixelpll,
\t\t\t\t\t   ctx->vm.pixelclock * clk_pixelpll_div * 8);
\t\t\tif (ret) {
\t\t\t\tpr_err("PB8 display PLL setup failed: %d\\n", ret);
\t\t\t\treturn ret;
\t\t\t}
\t\t}'''
    path.write_bytes(text.replace(anchor, anchor + addition).encode())


if __name__ == '__main__':
    import sys
    apply(sys.argv[1])
