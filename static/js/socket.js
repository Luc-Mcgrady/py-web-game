var socket = io()

socket.on('connect',() => {

    socket.on('redirect',(url) => {
        onbeforeunload = () => {}
        document.location.href = url
    })

    socket.on('setnum',(num) => {
        document.getElementById("vartext").value = num
    })
})