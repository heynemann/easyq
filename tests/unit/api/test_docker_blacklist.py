# Standard Library
from json import dumps
from uuid import uuid4

# 3rd Party
from preggy import expect

# Fastlane
from fastlane.worker.docker import BLACKLIST_KEY


def test_docker_blacklist1(client):
    """Test blacklisting a docker server"""

    def ensure_blacklist(method):
        docker_host = str(uuid4())

        data = {"host": docker_host}
        response = getattr(client, method)(
            "/docker-executor/blacklist", data=dumps(data), follow_redirects=True
        )

        expect(response.status_code).to_equal(200)
        expect(response.data).to_be_empty()

        app = client.application

        res = app.redis.exists(BLACKLIST_KEY)
        expect(res).to_be_true()

        res = app.redis.sismember(BLACKLIST_KEY, docker_host)
        expect(res).to_be_true()

    for method in ["post", "put"]:
        ensure_blacklist(method)


def test_docker_blacklist2(client):
    """
    Test blacklisting a docker server with invalid body or
    without a host property in the JSON body
    """

    def ensure_blacklist(method):
        response = getattr(client, method)(
            "/docker-executor/blacklist", data=dumps({}), follow_redirects=True
        )

        expect(response.status_code).to_equal(400)
        expect(response.data).to_be_like(
            "Failed to add host to blacklist because 'host' attribute was not found in JSON body."
        )

        app = client.application

        res = app.redis.exists(BLACKLIST_KEY)
        expect(res).to_be_false()

    for method in ["post", "put"]:
        ensure_blacklist(method)


def test_docker_blacklist3(client):
    """Test removing from blacklist a docker server"""
    docker_host = str(uuid4())

    data = {"host": docker_host}
    response = client.post(
        "/docker-executor/blacklist", data=dumps(data), follow_redirects=True
    )

    expect(response.status_code).to_equal(200)
    expect(response.data).to_be_empty()

    app = client.application

    res = app.redis.exists(BLACKLIST_KEY)
    expect(res).to_be_true()

    res = app.redis.sismember(BLACKLIST_KEY, docker_host)
    expect(res).to_be_true()

    data = {"host": docker_host}
    response = client.delete(
        "/docker-executor/blacklist", data=dumps(data), follow_redirects=True
    )

    expect(response.status_code).to_equal(200)
    expect(response.data).to_be_empty()

    app = client.application

    res = app.redis.exists(BLACKLIST_KEY)
    expect(res).to_be_false()


def test_docker_blacklist4(client):
    """
    Test removing a server from blacklist with invalid body or
    without a host property in the JSON body
    """

    response = client.delete(
        "/docker-executor/blacklist", data=dumps({}), follow_redirects=True
    )

    expect(response.status_code).to_equal(400)
    expect(response.data).to_be_like(
        "Failed to remove host from blacklist because 'host' attribute was not found in JSON body."
    )


def test_docker_blacklist5(client):
    """
    Test insert/remove a server in blacklist with invalid host, not following the model host:port
    """

    def ensure_blacklist(method):
        data = {"host": '000.000.000.000'}
        response = getattr(client, method)(
            "/docker-executor/blacklist", data=dumps(data), follow_redirects=True
        )

        expect(response.status_code).to_equal(400)
        expect(response.data).to_be_like(
            "Failed to add host to blacklist, we did not identify the formed 'host: port'"
        )

    for method in ["post", "put"]:
        ensure_blacklist(method)


def test_docker_blacklist6(client):
    """
    Test insert/remove a server with invalid port
    """

    def ensure_blacklist(method):

        data = {"host": '000.000.000.000:000a'}
        response = getattr(client, method)(
            "/docker-executor/blacklist", data=dumps(data), follow_redirects=True
        )

        expect(response.status_code).to_equal(400)
        expect(response.data).to_be_like(
            "Failed to add host to blacklist, the port is not an integer."
        )

    for method in ["post", "put"]:
        ensure_blacklist(method)
