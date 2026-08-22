using Google.Apis.Auth;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging.Abstractions;
using Plumbline.Worker.Push;

namespace Plumbline.Worker.Tests;

/// <summary>
/// The logic this project owns around Google's token validation: extracting the bearer
/// token, passing the right audience, and refusing a Google-signed token that is not
/// from the push service account.
/// </summary>
/// <remarks>
/// The signature/issuer/expiry checks belong to <c>GoogleJsonWebSignature</c> and are
/// not re-tested here — a fake validator stands in for them, because what can go quietly
/// wrong in this file is everything around that call. One test runs the real validator
/// against a malformed token to pin the seam itself: refusal, not an unhandled throw.
/// </remarks>
public class OidcPushAuthenticatorTests
{
    private const string Audience = "plumbline-ingestion-worker";
    private const string PushServiceAccount = "pubsub-push@plumbline-prod.iam.gserviceaccount.com";

    private static HttpRequest Request(string? authorization)
    {
        var context = new DefaultHttpContext();
        if (authorization is not null)
        {
            context.Request.Headers.Authorization = authorization;
        }
        return context.Request;
    }

    private static OidcPushAuthenticator Authenticator(
        Func<string, GoogleJsonWebSignature.ValidationSettings, Task<GoogleJsonWebSignature.Payload>> validate)
    {
        return new OidcPushAuthenticator(Audience, PushServiceAccount, NullLogger.Instance, validate);
    }

    private static GoogleJsonWebSignature.Payload PayloadFrom(string email, bool verified) => new()
    {
        Email = email,
        EmailVerified = verified,
    };

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("Basic dXNlcjpwYXNz")]
    [InlineData("bearer lowercase-scheme")]
    public async Task ARequestWithoutABearerTokenIsRefusedBeforeAnyValidation(string? authorization)
    {
        var authenticator = Authenticator((_, _) =>
            throw new InvalidOperationException("the validator must not be reached without a bearer token"));

        Assert.False(await authenticator.IsAuthenticAsync(Request(authorization)));
    }

    [Fact]
    public async Task TheTokenAndTheConfiguredAudienceReachTheValidator()
    {
        string? seenToken = null;
        GoogleJsonWebSignature.ValidationSettings? seenSettings = null;

        var authenticator = Authenticator((token, settings) =>
        {
            seenToken = token;
            seenSettings = settings;
            return Task.FromResult(PayloadFrom(PushServiceAccount, verified: true));
        });

        Assert.True(await authenticator.IsAuthenticAsync(Request("Bearer the-token")));
        Assert.Equal("the-token", seenToken);
        Assert.Equal(new[] { Audience }, seenSettings!.Audience);
    }

    [Fact]
    public async Task ATokenTheValidatorRejectsIsRefused()
    {
        var authenticator = Authenticator((_, _) =>
            throw new InvalidJwtException("JWT has expired"));

        Assert.False(await authenticator.IsAuthenticAsync(Request("Bearer expired")));
    }

    [Theory]
    [InlineData("someone-else@plumbline-prod.iam.gserviceaccount.com", true)]
    [InlineData("pubsub-push@plumbline-prod.iam.gserviceaccount.com", false)]
    [InlineData(null, true)]
    public async Task AGoogleSignedTokenFromAnyOtherIdentityIsRefused(string? email, bool verified)
    {
        // The audience check alone is not authentication: any principal with a Google
        // identity can mint a token naming this audience. The caller's verified email is
        // what makes the push service account the sole accepted identity.
        var authenticator = Authenticator((_, _) => Task.FromResult(PayloadFrom(email!, verified)));

        Assert.False(await authenticator.IsAuthenticAsync(Request("Bearer valid-but-wrong-caller")));
    }

    [Fact]
    public async Task TheCallerEmailComparisonIsCaseInsensitive()
    {
        var authenticator = Authenticator((_, _) =>
            Task.FromResult(PayloadFrom(PushServiceAccount.ToUpperInvariant(), verified: true)));

        Assert.True(await authenticator.IsAuthenticAsync(Request("Bearer valid")));
    }

    [Fact]
    public async Task TheRealValidatorRefusesAMalformedTokenAsARefusalNotACrash()
    {
        // The production seam, exercised once: GoogleJsonWebSignature throws
        // InvalidJwtException on a token that is not a JWT at all, before fetching any
        // certificate, and the authenticator turns that into a 401-shaped false.
        var authenticator = new OidcPushAuthenticator(Audience, PushServiceAccount,
            NullLogger<OidcPushAuthenticator>.Instance);

        Assert.False(await authenticator.IsAuthenticAsync(Request("Bearer not-a-jwt")));
    }
}
