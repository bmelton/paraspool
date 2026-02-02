// An actually universal spool rim adapter.
/* [parameters] */
// outer diameter of the spool rim
outer_diameter = 200; 
// text to be cut out of the nameplate. Leave blank to omit nameplate. Set to one space for an empty nameplate.
label_text = "Polymaker"; 

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
// font "Allerta Stencil" or another stencil font is needed
font = "Allerta Stencil:style=Regular";

/* [hidden] */  
$fn = 200;
inner_diameter = outer_diameter - (rim_width * 2);

module l_profile_ring() {
    union() {
        // horizontal face (rim)
        linear_extrude(wall_thickness)
            difference() {
                circle(d = outer_diameter);
                circle(d = inner_diameter);
            }
        
        // vertical face (lip)
        linear_extrude(lip_height)
            difference() {
                circle(d = outer_diameter);
                circle(d = outer_diameter - (wall_thickness * 2));
            }
    }
}

module nameplate_stencil() {
    infinite_width = outer_diameter;
    
    difference() {
        // 1. the shelf geometry (clipped to circle)
        intersection() {
            linear_extrude(wall_thickness)
                translate([-infinite_width/2, -(inner_diameter/2), 0])
                    square([infinite_width, plate_depth]);
            
            linear_extrude(wall_thickness)
                circle(d = inner_diameter);
        }
        
        // 2. the text cutout (stencil) with mirror fix
        if (label_text != "") {
            translate([0, -(inner_diameter/2) + (plate_depth/2), -1]) 
                linear_extrude(wall_thickness + 2) 
                    mirror([1, 0, 0]) // reverses text direction
                        text(label_text, size = font_size, halign = "center", valign = "center", font = font);
        }
    }
}

// assembly
l_profile_ring();
if (label_text != "") {
    nameplate_stencil();
}
