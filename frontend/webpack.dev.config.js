var config = require('./webpack.config')

config.devtool = 'eval-source-map'

config.devServer = {
    noInfo: true,
    proxy: {
        '/api/*': {
            target: 'http://localhost:8038',
            secure: false,
            rewrite: function(req) {
                // req.url = req.url.replace(/^\/api/, '');
            }
        }
    }
}
module.exports = config