$(document).ready(scannerSocket);

var scan_namespace = '/graph';
var ping_pong_times = [];
var graph_active = true;
var start_time;
var n_read;
var center_freq;
var minFreq, maxFreq;
var socket;

function pageInit(){
    $('#colScanner').hide();
    $('form#formStartScan').submit(formStartScan_submit);
    $('form#formDisconnect').submit(formDisconnect_submit);
    $('#formSaveSettings *').filter(':input').change(formSaveSettings_change);
    $('#inpFreqMax').keypress(inputKeyPress);
    $('#inpFreqMin').keypress(inputKeyPress);
    $('#inpDevIndex').keypress(inputKeyPress);
    $('#inpSampRate').keypress(inputKeyPress);
    $('#inpInterval').keypress(inputKeyPress);
}
function formStartScan_submit(event){
    if (graph_active){
        socket.emit('start_sdr');
    }else{
        socket.emit('stop_sdr');
    }
    return false;
}
function formDisconnect_submit(event){
    socket.emit('disconnect_request');
    on_log_message("Disconnecting...")
    setTimeout(function() {
        location.reload();
    }, 2000);
    return false;
}
function formSaveSettings_change(){
    var args = {
        'dev': parseInt($('#inpDevIndex').val()), 
        'samprate': parseInt($('#inpSampRate').val()), 
        'gain': $('#inpDevGain').val(), 
        'freq': center_freq,
        'n': n_read,
        'i': parseInt($('#inpInterval').val())
    };
    if(checkArgs(args)){
        socket.emit('update_settings', args);
    }else{
        socket.emit('send_cli_args');
    }
}
function inputKeyPress(evt){
    var charCode = (evt.which) ? evt.which : event.keyCode
    if (charCode > 31 && (charCode < 48 || charCode > 57))
        return false;
    return true;
}
function checkRange(){
    minFreq = parseInt($('#inpFreqMin').val());
    maxFreq = parseInt($('#inpFreqMax').val());
    if(maxFreq > minFreq)
        return true;
    return false;
}
function setRange(freq){
    $('#inpFreqMin').val(parseInt(+freq - (freq/5)));
    $('#inpFreqMax').val(parseInt(+freq + (freq/5)));
}
function checkArgs(args){
    if (args['dev'] < 0 || args['dev'] > 20 || args['samprate'] < 0 || 
    args['gain'] < 0  || args['i'] < 0 || !checkRange()){
        on_log_message("Invalid settings detected.");
        $('#spnSettingsLog').text('Invalid settings detected.');
        setTimeout(function() {
            $('#spnSettingsLog').text('');
        }, 1000);
        $('#btnStartScan').prop("disabled", true);
        return false;
    }
    $('#btnStartScan').prop("disabled", false);
    return true;
}
function on_log_message(msg){
    current_time = new Date().toLocaleTimeString().split(' ')[0];
    $('#divLog').append("<b>[" + current_time + "]</b> " + msg + "<br>");
    $('#divLog').scrollTop($('#divLog').height());
}
function scannerSocket(){
    pageInit();
    socket = io.connect(location.protocol + '//' + document.domain + 
                 ':' + location.port + scan_namespace);

    socket.on('connect', function() {
        socket.emit('send_cli_args');
    });

    socket.on('log_message', function(log) {
        on_log_message(log.msg);   
    });

    socket.on('dev_status', function(status) {
        if(parseInt(status) == 0){
            $('#formSaveSettings :input').prop('disabled', false);
            $('#formDisconnect :input').prop('disabled', false);
            graph_active = true;
            $('#btnStartScan').val("Start Scan");            
        }else if(parseInt(status) == 1) {
            $('#formSaveSettings :input').prop('disabled', true);
            $('#formDisconnect :input').prop('disabled', true);
            graph_active = false;
            $('#btnStartScan').val("Stop Scan");
        }
    });

    socket.on('fft_data', function(msg) {
        $('#imgFreqScan').attr("src", "data:image/png;base64," + msg.data);
        if(!$('#colScanner').is(':visible')){
            $('#colScanner').show();
        }
    });

    socket.on('cli_args', function(cliargs) {
        var args = cliargs.args;
        for (var i in args){
            if (i != 'freq')
                args[i] = args[i] || 0;
        }
        checkArgs(args);
        $("#inpDevIndex").val(args.dev);
        $("#inpSampRate").val(args.samprate);
        $("#inpDevGain").val(args.gain);
        $("#inpInterval").val(args.i);
        center_freq = args.freq;
        n_read = args.n;
        if (cliargs.status == 1){
            $('#spnSettingsLog').text('Settings saved.');
            setTimeout(function() {
                $('#spnSettingsLog').text('');
            }, 1000);
        }else{
            if(center_freq > 0)
                setRange(center_freq);
        }
    });

    socket.on('server_pong', function() {
        var latency = (new Date).getTime() - start_time;
        ping_pong_times.push(latency);
        ping_pong_times = ping_pong_times.slice(-30);11
        var sum = 0;
        for (var i = 0; i < ping_pong_times.length; i++)
            sum += ping_pong_times[i];
        $('#spnPingPong').text(Math.round(10 * sum / ping_pong_times.length) / 10 + "ms");
    });
    
    window.setInterval(function() {
        start_time = (new Date).getTime();
        socket.emit('server_ping');
    }, 1000);
}