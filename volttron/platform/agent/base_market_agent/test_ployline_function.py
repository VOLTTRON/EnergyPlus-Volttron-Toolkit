from poly_line import PolyLine
from point import Point
from poly_line_factory import PolyLineFactory


demand_curve1 = PolyLine()

demand_curve2 = PolyLine()

demand_curve3 = PolyLine()

demand_curve1.add(Point(price=0.1, quantity=100))

demand_curve1.add(Point(price=1, quantity=1))


demand_curve2.add(Point(price=0.2, quantity=100))

demand_curve2.add(Point(price=0.8, quantity=1))


demand_curve3.add(Point(price=-0.2, quantity=100))

demand_curve3.add(Point(price=0.8, quantity=1))

curves = [demand_curve1, demand_curve2, demand_curve3]
combined_curves = PolyLineFactory.combine(curves, 6)

for point in combined_curves.points:
     print point


