// An actually universal spool rim adapter.
/* [parameters] */
// The actual diameter of the cardboard spool (measure this!)
spool_diameter = 194;

// Extra clearance so the adapter slides on easily (0.2 - 0.5 recommended)
tolerance = 0.2;

// text to be cut out of the nameplate.
label_text = "AICOPYTO";

// width of the horizontal rim face, in mm
rim_width = 6;
// height of the vertical lip face, in mm
lip_height = 6;

// thickness of the L-profile walls, in mm
wall_thickness = 1;

// font size for the label
font_size = 8;

// how far the plate extends from the inner edge toward the center
plate_depth = 17;
// font
font = "Allerta Stencil:style=Regular";

/* [hidden] */
$fn = 200;

// Logic Fix: Calculate dimensions based on the SPOOL being the inside
// The hole in the lip must be Spool + Tolerance
lip_inner_diameter = spool_diameter + tolerance;

// The outside of the lip is the Hole + Walls
lip_outer_diameter = lip_inner_diameter + (wall_thickness * 2);

// The hole in the center of the ring (visual only)
center_hole_diameter = lip_inner_diameter - (rim_width * 2);

module l_profile_ring() {
    union() {
        // horizontal face (rim) - Fits against the side of the spool
        linear_extrude(wall_thickness)
            difference() {
                circle(d = lip_outer_diameter);
                circle(d = center_hole_diameter);
            }

        // vertical face (lip) - Sleeves over the edge of the spool
        linear_extrude(lip_height)
            difference() {
                circle(d = lip_outer_diameter);
                // This is now defined by the spool size + tolerance
                circle(d = lip_inner_diameter);
            }
    }
}

module nameplate_stencil() {
    // infinite_width just needs to be wide enough to cut the shape
    infinite_width = lip_outer_diameter;

    difference() {
        // 1. the shelf geometry (clipped to circle)
        intersection() {
            linear_extrude(wall_thickness)
                translate([-infinite_width/2, -(center_hole_diameter/2), 0])
                    square([infinite_width, plate_depth]);

            linear_extrude(wall_thickness)
                circle(d = center_hole_diameter);
        }

        // 2. the text cutout (stencil) with mirror fix
        if (label_text != "") {
             // Adjusted translation to account for new center_hole logic
            translate([0, -(center_hole_diameter/2) + (plate_depth/2), -1])
                linear_extrude(wall_thickness + 2)
                    mirror([1, 0, 0]) // reverses text direction for face-down printing
                        text(label_text, size = font_size, halign = "center", valign = "center", font = font);
        }
    }
}

// assembly
l_profile_ring();
if (label_text != "") {
    nameplate_stencil();
}
