-- Fluke NetDAQ dissector for wireshark
-- (c) fenugrec 2025
--
-- place or symlink in $HOME/.local/lib/wireshark/plugins
-- to reload : Analyze->reload LUA plugins

netdaq_protocol = Proto("netdaq", "Fluke NetDAQ protocol")

seq_id   = ProtoField.uint32("netdaq.seq_id"   , "seq_id"  , base.DEC)
cmd  = ProtoField.uint32("netdaq.cmd"  , "cmd"  , base.HEX)
pkt_len     = ProtoField.uint32("netdaq.pkt_len"    , "pkt_len"    , base.DEC)

netdaq_protocol.fields = { message_length, seq_id, cmd, pkt_len }

function netdaq_protocol.dissector(buffer, pinfo, tree)
 length = buffer:len()
 if length == 0 then return end

 pinfo.cols.protocol = netdaq_protocol.name

 local subtree = tree:add(netdaq_protocol, buffer(), "netdaq Protocol Data")

-- subtree:add(magic, buffer(0,4)) -- "FELX" header
 subtree:add(seq_id,   buffer(4,4))
 subtree:add(cmd,  buffer(8,4))
 subtree:add(pkt_len,     buffer(12,4))
end

local tcp_port = DissectorTable.get("tcp.port")
tcp_port:add(4369, netdaq_protocol)

