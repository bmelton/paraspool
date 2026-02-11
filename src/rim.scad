// An actually universal cardboard spool rim adapter for AMSes.

/* [Preset Selection] */
// Select your spool brand. Choose "Custom" to use manual settings below.
spool_type = "AICOPYTO"; // [AICOPYTO, DEEPLEE, Elegoo, Inland, Overture, Polymaker, Sunlu, Custom]

/* [Manual Settings] */
// Only used if spool_type is "Custom". Diameter of the cardboard spool.
manual_spool_diameter = 200;

// Only used if spool_type is "Custom". Text to be cut out.
manual_label_text = "CUSTOM";

/* [General Parameters] */
// Extra clearance so the adapter slides on easily
tolerance = 0.4;

// Width of the horizontal rim face
rim_width = 6;

// Height of the vertical lip face
lip_height = 6;

// Thickness of the L-profile walls
wall_thickness = 1;

// Font size for the label
font_size = 8;

// How far the plate extends from the inner edge toward the center
plate_depth = 17;

// Font: If you don't use a stencil font, the center of your letters will fall out. It's not a problem really, but be warned.
font = "Allerta Stencil:style=Regular";

/* [hidden] */
$fn = 200;

// PRESETS
// Units: 196mm (7.72"), 200mm (7.87")

// 1. Determine Diameter
spool_diameter = 
    (spool_type == "AICOPYTO") ? 193 : 
    (spool_type == "DEEPLEE") ? 195.8 :
    (spool_type == "Elegoo")   ? 199 : 
    (spool_type == "Inland")   ? 199 : 
    (spool_type == "Overture") ? 199.5 :
    (spool_type == "Polymaker") ? 199.5 :  
    (spool_type == "Sunlu") ? 199.5 :
    manual_spool_diameter;             // defaults to custom

// 2. Determine Label
label_text = 
    (spool_type == "AICOPYTO") ? "AICOPYTO" : 
    (spool_type == "DEEPLEE") ? "DEEPLEE" :
    (spool_type == "Elegoo")   ? "ELEGOO" : 
    (spool_type == "Inland")   ? "INLAND" : 
    (spool_type == "Overture") ? "OVERTURE" :
    (spool_type == "Polymaker") ? "POLYMAKER" :
    (spool_type == "Sunlu") ? "SUNLU" :
    manual_label_text;                 // defaults to custom

// Calculated dimensions
// lip_inner_diameter: spool_diameter + tolerance
// 196mm + 0.2mm = 196.2mm (7.724")
lip_inner_diameter = spool_diameter + tolerance;
lip_outer_diameter = lip_inner_diameter + (wall_thickness * 2);
center_hole_diameter = lip_inner_diameter - (rim_width * 2);

module l_profile_ring() {
    union() {
        // horizontal face (rim)
        linear_extrude(wall_thickness)
            difference() {
                circle(d = lip_outer_diameter);
                circle(d = center_hole_diameter);
            }

        // vertical face (lip)
        linear_extrude(lip_height)
            difference() {
                circle(d = lip_outer_diameter);
                circle(d = lip_inner_diameter);
            }
    }
}

module nameplate_stencil() {
    infinite_width = lip_outer_diameter;

    difference() {
        intersection() {
            linear_extrude(wall_thickness)
                translate([-infinite_width/2, -(center_hole_diameter/2), 0])
                    square([infinite_width, plate_depth]);

            linear_extrude(wall_thickness)
                circle(d = center_hole_diameter);
        }

        if (label_text != "") {
            translate([0, -(center_hole_diameter/2) + (plate_depth/2), -1])
                linear_extrude(wall_thickness + 2)
                    mirror([1, 0, 0]) 
                        text(label_text, size = font_size, halign = "center", valign = "center", font = font);
        }
    }
}

// assembly
l_profile_ring();
if (label_text != "") {
    nameplate_stencil();
}