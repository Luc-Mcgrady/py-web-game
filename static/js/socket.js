var socket = io()
var key_handle_json = {}

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
function get_state(keys) {
    socket.emit("game_state",keys)
}

socket.on('game_state_return',(dict,keys) => {
    handle_keys(dict,keys,key_handle_json)
})
socket.on('redirect',(url) => {
    onbeforeunload = () => {}
    document.location.href = url
})
