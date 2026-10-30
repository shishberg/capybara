// A low-profile Capybara: the parametric chassis. See README.md.
//
//   half  "right" or "left" (the left is the right mirrored)
//   show  "assembly"  body, bottom plate, switches, caps, sockets, diodes and electronics
//         "body"      the body alone, this way up, to print
//         "plate"     the bottom plate alone, to print
//         "blank"     the body before anything is cut from it
//         "keys"      switches, caps and electronics on their own
//         "check"     where caps meet (empty when the layout is clear)
//         "section"   the assembly cut through the home row
//   open  how far the bottom plate drops below the body in the assembly
//
// Render one part to STL from the shell, e.g.:
//   openscad -D 'show="body"' -D 'half="left"' -o left-body.stl capybara-lowpro.scad
// Any parameter in params.scad can be overridden the same way (-D 'tent_deg=4').
half = "right";
show = "assembly";
open = 0;
include <chassis.scad>

echo(report());

module assembly() {
  color("burlywood") body();
  color("peru") translate([0, 0, -open]) bottom_plate();
  switches();
  keycaps();
  sockets();
  diodes();
  electronics();
}
module shown() {
  if (show == "assembly") assembly();
  else if (show == "body") color("burlywood") body();
  else if (show == "plate") color("peru") bottom_plate();
  else if (show == "blank") blank();
  else if (show == "keys") { switches(); keycaps(); sockets(); electronics(); }
  else if (show == "check") color("red") cap_collisions();
  else if (show == "section") intersection() {
    assembly();
    translate([BBOX[0][0], BBOX[0][1] - 50, -10]) cube([BBOX[1][0] - BBOX[0][0], 50 + origin(key_named("middle_0")[K_FRAME])[1], 100]);
  }
}
if (half == "left") mirror([1, 0, 0]) shown(); else shown();
