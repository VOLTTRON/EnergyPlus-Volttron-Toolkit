from flask import Flask, request, current_app
from flask_restful import Resource, Api
from flask_restful.utils import cors

from src.power_data import PowerData
from src.zone_data import ZoneData
from src.simulation_data import SimulationData


app = Flask(__name__, static_folder='static', static_url_path='')
api = Api(app, decorators=[cors.crossdomain(origin='*')])


class Root(Resource):
    def get(self):
        return current_app.send_static_file('index.html')

#api.add_resource(ZoneDataByDate, '/api/ZoneData/<string:date>')
api.add_resource(ZoneData, '/api/ZoneData/<int:resource_id>')
api.add_resource(PowerData, '/api/PowerData')
api.add_resource(SimulationData, '/api/SimulationData')
api.add_resource(Root, '/')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
