import asyncio, struct
from bless import BlessServer, GATTCharacteristicProperties, GATTAttributePermissions
SVC="7e4e1701-1ea6-40c9-9dcc-13d34ffead57"
D="7e4e1702-1ea6-40c9-9dcc-13d34ffead57"; C="7e4e1703-1ea6-40c9-9dcc-13d34ffead57"
async def main():
    s=BlessServer(name="Progressor_1234", loop=asyncio.get_running_loop())
    s.read_request_func=lambda ch,**k: ch.value or b""
    s.write_request_func=lambda ch,v,**k: print("write:",bytes(v).hex())
    await s.add_new_service(SVC)
    await s.add_new_characteristic(SVC,D,
        GATTCharacteristicProperties.read|GATTCharacteristicProperties.notify,
        None, GATTAttributePermissions.readable)
    await s.add_new_characteristic(SVC,C,
        GATTCharacteristicProperties.write|GATTCharacteristicProperties.write_without_response,
        None, GATTAttributePermissions.writeable)
    await s.start()
    print("ADVERTISING OK as Progressor_1234")
    ch=s.get_characteristic(D); ch.value=bytes([1,8])+struct.pack("<fI",12.5,1000)
    s.update_value(SVC,D)
    print("notify push OK")
    await asyncio.sleep(5)
    await s.stop(); print("stopped cleanly")
asyncio.run(main())
