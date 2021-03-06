# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import paxos_pb2 as paxos__pb2


class ChatterStub(object):
  """Interface exported by the server.
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.SendChatMessage = channel.unary_unary(
        '/paxos.Chatter/SendChatMessage',
        request_serializer=paxos__pb2.ChatRequest.SerializeToString,
        response_deserializer=paxos__pb2.ChatReply.FromString,
        )
    self.GetData = channel.unary_unary(
        '/paxos.Chatter/GetData',
        request_serializer=paxos__pb2.Empty.SerializeToString,
        response_deserializer=paxos__pb2.DataReply.FromString,
        )


class ChatterServicer(object):
  """Interface exported by the server.
  """

  def SendChatMessage(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def GetData(self, request, context):
    """sends back views and log hashes
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_ChatterServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'SendChatMessage': grpc.unary_unary_rpc_method_handler(
          servicer.SendChatMessage,
          request_deserializer=paxos__pb2.ChatRequest.FromString,
          response_serializer=paxos__pb2.ChatReply.SerializeToString,
      ),
      'GetData': grpc.unary_unary_rpc_method_handler(
          servicer.GetData,
          request_deserializer=paxos__pb2.Empty.FromString,
          response_serializer=paxos__pb2.DataReply.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'paxos.Chatter', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))


class PaxosStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.Prepare = channel.unary_unary(
        '/paxos.Paxos/Prepare',
        request_serializer=paxos__pb2.PrepareSend.SerializeToString,
        response_deserializer=paxos__pb2.PromiseReply.FromString,
        )
    self.Accept = channel.unary_unary(
        '/paxos.Paxos/Accept',
        request_serializer=paxos__pb2.AcceptSend.SerializeToString,
        response_deserializer=paxos__pb2.AcceptReply.FromString,
        )
    self.Learn = channel.unary_unary(
        '/paxos.Paxos/Learn',
        request_serializer=paxos__pb2.LearnSend.SerializeToString,
        response_deserializer=paxos__pb2.LearnReply.FromString,
        )
    self.HeartBeat = channel.unary_unary(
        '/paxos.Paxos/HeartBeat',
        request_serializer=paxos__pb2.Empty.SerializeToString,
        response_deserializer=paxos__pb2.HBReply.FromString,
        )


class PaxosServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def Prepare(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Accept(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Learn(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def HeartBeat(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_PaxosServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'Prepare': grpc.unary_unary_rpc_method_handler(
          servicer.Prepare,
          request_deserializer=paxos__pb2.PrepareSend.FromString,
          response_serializer=paxos__pb2.PromiseReply.SerializeToString,
      ),
      'Accept': grpc.unary_unary_rpc_method_handler(
          servicer.Accept,
          request_deserializer=paxos__pb2.AcceptSend.FromString,
          response_serializer=paxos__pb2.AcceptReply.SerializeToString,
      ),
      'Learn': grpc.unary_unary_rpc_method_handler(
          servicer.Learn,
          request_deserializer=paxos__pb2.LearnSend.FromString,
          response_serializer=paxos__pb2.LearnReply.SerializeToString,
      ),
      'HeartBeat': grpc.unary_unary_rpc_method_handler(
          servicer.HeartBeat,
          request_deserializer=paxos__pb2.Empty.FromString,
          response_serializer=paxos__pb2.HBReply.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'paxos.Paxos', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
