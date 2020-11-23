key_handle_json = {"boxes":(a)=>{console.log("Remaining numbers: " + String(a))}, "target":(a)=>{console.log("target: " + String(a))}}

function send_choices(choices) {
    socket.emit("game_action","boxes",choices)
}
function restart() {
    socket.emit("game_action","restart")
}

socket.on('game_over',(name) => {
    get_state()
    console.log(name + " Wins!")
})
socket.on('game_turn',(name) => {
    console.log(name + "'s turn")
    get_state()
})