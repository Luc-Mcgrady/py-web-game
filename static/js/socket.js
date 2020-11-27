var socket = io() // https://socket.io/docs/v3/index.html
var key_handle_json = {} // This will be a list of functions that do things with whatever values are in the game state dict

function handle_keys(json,keys,key_handlers) {
	
	if (keys === undefined)
		keys = []
	
	keys.forEach((key) => {
		json = json[key]
		key_handlers = key_handlers[key]
	})
	
	for (const key in key_handlers) {
		key_handlers[key](json[key])
	}
}
function get_state(keys) { // Used to ask the server for an update on what the current game_state is
    socket.emit("game_state",keys)
}

socket.on('game_state_return',(dict,keys) => { // Whenever a gamestate is recived it is handled specialy.
    handle_keys(dict,keys,key_handle_json)
})
socket.on('redirect',(url) => {
    onbeforeunload = () => {}
    document.location.href = url
}) // You can add other "universal" events here.
